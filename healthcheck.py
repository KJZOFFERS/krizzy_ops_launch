from aiohttp import web


async def health(request):
    return web.json_response({"status": "ok"})


def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health)
    web.run_app(app, port=8080)
