import asyncio, os, importlib, traceback
from aiohttp import web
from dotenv import load_dotenv
from krizzy_ops.utils.discord_utils import post_log, post_error
from krizzy_ops.engines import watchdog
from krizzy_ops.utils import llm_control

load_dotenv()
PORT = int(os.getenv("PORT", "8080"))

async def run_engine(name: str, module_path: str, func_name: str):
    while True:
        try:
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            await func()
        except Exception as e:
            err = traceback.format_exc()
            await post_error(f"{name} crashed: {e}")
            await llm_control.llm_rewrite(module_path.replace(".", "/") + ".py", err)
            try:
                module = importlib.import_module(module_path)
                importlib.reload(module)
            except Exception as reload_err:
                await post_error(f"Reload failed for {name}: {reload_err}")
        await asyncio.sleep(5)

async def on_start(app):
    await post_log("🚀 KRIZZY OPS Supervisor Live.")
    app["tasks"] = [
        asyncio.create_task(run_engine("rei_dispo", "krizzy_ops.engines.rei_dispo", "loop_once")),
        asyncio.create_task(run_engine("govcon_subtrap", "krizzy_ops.engines.govcon_subtrap", "loop_once")),
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
