import aiohttp, os, logging
from utils.airtable_utils import write_record
from utils.discord_utils import send_message

logger = logging.getLogger("data_extraction")

async def fetch_json(url, params=None):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=30) as r:
                if r.status == 200:
                    return await r.json()
                logger.error(f"Fetch failed {r.status}: {url}")
    except Exception as e:
        logger.error(f"Fetch error: {e}")
    return None

async def extract_sam_gov_opportunities():
    base_url = os.getenv("SAM_FEED_URL", "https://api.sam.gov/prod/opportunities/v1/search")
    params = {"api_key": os.getenv("SAM_API_KEY"),
              "noticeType": "Combined Synopsis/Solicitation", "limit": 5}
    data = await fetch_json(base_url, params=params)
    if not data or "opportunitiesData" not in data:
        return []
    return [{"Solicitation": d.get("solicitationNumber"),
             "Title": d.get("title"),
             "Agency": d.get("agency"),
             "DueDate": d.get("responseDate")} for d in data["opportunitiesData"]]

async def extract_rei_deals():
    return [
        {"Property": "1247 Oak St", "City": "Atlanta", "Price": 85000, "ARV": 145000},
        {"Property": "3421 Pine Ave", "City": "Birmingham", "Price": 67000, "ARV": 115000}
    ]

async def run_data_cycle():
    rei = await extract_rei_deals()
    govcon = await extract_sam_gov_opportunities()
    for deal in rei: write_record("Leads_REI", deal)
    for bid in govcon: write_record("GovCon_Opportunities", bid)
    send_message("DISCORD_WEBHOOK_OPS",
                 f"Data updated: {len(rei)} REI, {len(govcon)} GovCon")
