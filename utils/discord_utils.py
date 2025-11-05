import aiohttp, asyncio, logging, os

OPS_WEBHOOK = os.getenv("DISCORD_OPS_WEBHOOK")
ERROR_WEBHOOK = os.getenv("DISCORD_ERROR_WEBHOOK")

async def _do(url: str, payload: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as r:
                return await r.text()
    except Exception as e:
        logging.error(f"Discord post failed: {e}")
        return None

def post_ops(msg: str):
    asyncio.create_task(_do(OPS_WEBHOOK, {"content": msg}))

def post_error(msg: str):
    asyncio.create_task(_do(ERROR_WEBHOOK, {"content": msg}))

def send_message(url: str, msg: str):
    asyncio.create_task(_do(url, {"content": msg}))
