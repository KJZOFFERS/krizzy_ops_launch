from __future__ import annotations

from aiohttp import web


async def health(request: web.Request) -> web.Response:
    from datetime import datetime

    return web.json_response({"status": "ok", "ts": datetime.utcnow().isoformat()})


def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health)
    web.run_app(app, port=8080)
