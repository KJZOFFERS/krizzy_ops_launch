import asyncio, os, importlib, traceback
from aiohttp import web
from dotenv import load_dotenv
from utils.discord_utils import post_log, post_error
from engines import rei_dispo, govcon_subtrap, watchdog
from utils import llm_control

load_dotenv()
PORT = int(os.getenv("KRIZZY_PORT", "8080"))

async def run_engine(name, func):
    while True:
        try:
            await func()
        except Exception as e:
            err = traceback.format_exc()
            await post_error(f"{name} crashed: {e}")
            await llm_control.llm_rewrite(f"engines/{name}", err)
            importlib.reload(func.__module__)
        await asyncio.sleep(5)

async def on_start(app):
    await post_log("🚀 KRIZZY OPS Supervisor Live.")
    app["tasks"] = [
        asyncio.create_task(run_engine("rei_dispo", rei_dispo.loop_once)),
        asyncio.create_task(run_engine("govcon_subtrap", govcon_subtrap.loop_once)),
        asyncio.create_task(watchdog.loop_forever(app["state"]))
    ]

async def on_cleanup(app):
    for t in app.get("tasks", []):
        t.cancel()

async def health(_):
    return web.json_response({"status": "ok"})

def create_app():
    app = web.Application()
    app["state"] = {}
    app.add_routes([web.get("/health", health)])
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_cleanup)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)