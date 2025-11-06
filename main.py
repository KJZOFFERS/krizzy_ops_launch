from __future__ import annotations
import json, os
from loguru import logger
# Try FastAPI mode; else fall back to stdlib HTTP server so offline envs still run.
try:
    from fastapi import FastAPI, Body
    from fastapi.responses import JSONResponse, PlainTextResponse
    from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
    FASTAPI = True
except Exception:
    FASTAPI = False
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
    from threading import Thread
    import time
from config import get_settings
from utils.kpi import log_kpi
if FASTAPI:
    app = FastAPI(title="Krizzy Ops Web", version="1.0.0")
    REQUESTS_TOTAL = Counter("http_requests_total","HTTP requests",["path","method","status"])
    @app.middleware("http")
    async def _m(request, call_next):
        r = await call_next(request)
        try: REQUESTS_TOTAL.labels(path=request.url.path,method=request.method,status=str(r.status_code)).inc()
        except Exception: pass
        return r
    @app.get("/health")
    async def health():
        s = get_settings()
        return {"status":"healthy","service":s.service_name}
    @app.get("/metrics")
    async def metrics():
        data = generate_latest()
        return PlainTextResponse(content=data, media_type=CONTENT_TYPE_LATEST)
    @app.post("/command")
    async def command(payload: dict = Body(...)):
        cmd = str(payload.get("input","" )).strip()
        await log_kpi("command_invocation", 1, {"input": cmd})
        return {"ok": True, "received": cmd}
    @app.get("/")
    async def root(): return JSONResponse({"ok": True})
else:
    # Minimal offline HTTP server
    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, obj):
            data = json.dumps(obj).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            if self.path.startswith("/health"):
                s = get_settings()
                self._json(200, {"status":"healthy","service":s.service_name})
            elif self.path.startswith("/metrics"):
                body = b"# offline metrics\n"
                self.send_response(200); self.send_header("Content-Type","text/plain"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
            else:
                self._json(200, {"ok": True})
        def do_POST(self):
            if self.path.startswith("/command"):
                length = int(self.headers.get("Content-Length","0"))
                raw = self.rfile.read(length) if length else b"{}"
                try: payload = json.loads(raw.decode("utf-8"))
                except Exception: payload = {}
                cmd = str(payload.get("input","" )).strip()
                import asyncio; asyncio.run(log_kpi("command_invocation",1,{"input":cmd}))
                self._json(200, {"ok": True, "received": cmd})
            else:
                self._json(404, {"ok": False})
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer): daemon_threads = True
    def serve(port:int= int(os.getenv("PORT","8080"))):
        srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        logger.info(f"Offline server listening on :{port}")
        srv.serve_forever()
    if __name__ == "__main__":
        serve()
