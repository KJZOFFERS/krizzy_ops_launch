# FILE: data_extraction.py
import httpx
from utils.discord_utils import post_error

async def extract_data(url: str):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as e:
        post_error(f"Data extraction failed: {e}")
        return None
