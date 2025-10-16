from aiohttp import web

async def health(_):
    return web.json_response({"status":"ok"})
