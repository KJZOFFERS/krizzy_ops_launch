import asyncio, os, importlib, traceback, inspect
from aiohttp import web
from dotenv import load_dotenv
from utils.discord_utils import post_log, post_error
from engines import rei_dispo, govcon_subtrap, watchdog
from utils import llm_control

load_dotenv()
PORT = int(os.getenv("PORT", "8080"))


async def _reload_module(module):
    try:
        importlib.reload(module)
        await post_log(f"♻️ Reloaded module {module.__name__}")
    except Exception:
        await post_error(f"Failed to reload module {module.__name__}:\n{traceback.format_exc()}")


async def run_engine(name: str, module, func_attr: str):
    """Run an engine function in a supervised loop with hot-reload on crash.

    We reload the whole module and then rebind the function name on failure.
    """
    while True:
        try:
            func = getattr(module, func_attr)
            await func()
        except Exception as e:
            err = traceback.format_exc()
            await post_error(f"{name} crashed: {e}")
            # Try to have the LLM propose a fix directly to the engine file path
            try:
                # Resolve source file of the module (fallback to engines/<name>.py)
                src_file = inspect.getsourcefile(module) or os.path.join(os.path.dirname(__file__), "engines", f"{name}.py")
                await llm_control.llm_rewrite(src_file, err)
            except Exception:
                await post_error(f"LLM rewrite failed for {name}:\n{traceback.format_exc()}")
            # Reload module so subsequent iterations use updated code
            await _reload_module(module)
        await asyncio.sleep(5)


async def on_start(app: web.Application):
    await post_log("🚀 KRIZZY OPS Supervisor Live.")
    app["tasks"] = [
        asyncio.create_task(run_engine("rei_dispo", rei_dispo, "loop_once")),
        asyncio.create_task(run_engine("govcon_subtrap", govcon_subtrap, "loop_once")),
        asyncio.create_task(watchdog.loop_forever(app["state"]))
    ]


async def on_cleanup(app: web.Application):
    for t in app.get("tasks", []):
        t.cancel()


async def health(_):
    return web.json_response({"status": "ok"})


def create_app() -> web.Application:
    app = web.Application()
    app["state"] = {}
    app.add_routes([web.get("/health", health)])
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
