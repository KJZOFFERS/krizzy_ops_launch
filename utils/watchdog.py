import asyncio, logging

async def heartbeat():
    while True:
        logging.info("KRIZZY OPS heartbeat active")
        await asyncio.sleep(60)
