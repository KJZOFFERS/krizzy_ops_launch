import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from pydantic import BaseModel

from utils.discord_utils import post_ops, post_error
from utils.airtable_utils import kpi_log_safe

SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")
ENV = os.getenv("ENV", "production")

app = FastAPI(title="KRIZZY OPS Web", version="1.0.0")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.on_event("startup")
async def on_startup():
    # Non-blocking notifications/metrics (safe no-op if envs not present)
    await post_ops(f"✅ {SERVICE_NAME} online | env={ENV} | ts={now_iso()}")
    await kpi_log_safe(
        event="web_online",
        meta={"env": ENV, "service": SERVICE_NAME, "ts": now_iso()},
    )


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "env": ENV,
        "timestamp": now_iso(),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/healthz")
async def healthz():
    # Legacy path retained
    return {"status": "healthy", "service": SERVICE_NAME}


class HeartbeatIn(BaseModel):
    note: Optional[str] = None
    kpi_tag: Optional[str] = "manual"


@app.post("/kpi/heartbeat")
async def heartbeat(payload: HeartbeatIn):
    # Writes to Airtable KPI_Log if configured (safe no-op otherwise)
    meta = {"note": payload.note, "kpi_tag": payload.kpi_tag, "env": ENV}
    ok = await kpi_log_safe(event="heartbeat", meta=meta)
    return {"logged": ok, "service": SERVICE_NAME, "timestamp": now_iso()}


@app.post("/twilio/inbound")
async def twilio_inbound(request: Request, bg: BackgroundTasks):
    # Twilio posts application/x-www-form-urlencoded
    form = await request.form()
    from_num = form.get("From")
    body = form.get("Body")
    sid = form.get("MessageSid")

    if not body:
        raise HTTPException(status_code=400, detail="Missing Body")

    msg = f"📩 Twilio inbound | from={from_num} | sid={sid}\n```\n{body}\n```"
    bg.add_task(post_ops, msg)

    await kpi_log_safe(
        event="twilio_inbound",
        meta={"from": from_num, "sid": sid, "len": len(body or "")},
    )

    # Return empty TwiML to acknowledge
    return {
        "received": True,
        "service": SERVICE_NAME,
        "sid": sid,
        "timestamp": now_iso(),
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Never crash silently; report to Discord + KPI
    detail = {
        "path": str(request.url),
        "method": request.method,
        "error": repr(exc),
        "ts": now_iso(),
    }
    await post_error(f"🔥 Exception\n```json\n{json.dumps(detail, indent=2)}\n```")
    await kpi_log_safe(event="exception", meta=detail)
    return {"error": "internal_error", "detail": detail}
