
import aiohttp, asyncio
from utils.airtable_utils import safe_airtable_write
from utils.discord_utils import post_error

async def extract_data(url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.text()
                return data
    except Exception as e:
        post_error(f"Data extraction failed: {e}")
        return None
