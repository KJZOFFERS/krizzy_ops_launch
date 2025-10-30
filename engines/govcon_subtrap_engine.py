import asyncio
import aiohttp
import csv
import os
import time
import requests

def upsert_record(table, key_field, key_value, data):
    airtable_base = os.getenv("AIRTABLE_BASE_ID")
    airtable_key = os.getenv("AIRTABLE_API_KEY")
    url = f"https://api.airtable.com/v0/{airtable_base}/{table}"
    headers = {
        "Authorization": f"Bearer {airtable_key}",
        "Content-Type": "application/json"
    }
    query = {
        "filterByFormula": f"{{{key_field}}}='{key_value}'"
    }
    existing = requests.get(url, headers=headers, params=query).json()
    if existing.get("records"):
        return False
    payload = {"fields": data}
    res = requests.post(url, headers=headers, json=payload)
    return res.status_code == 200 or res.status_code == 201

def send_discord(channel, msg):
    webhook = os.getenv(f"DISCORD_WEBHOOK_{channel.upper()}")
    if webhook:
        try:
            requests.post(webhook, json={"content": msg})
        except Exception:
            pass

def send_sms(phone, msg):
    from twilio.rest import Client
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
    if not all([sid, token, from_number]):
        return
    try:
        client = Client(sid, token)
        client.messages.create(body=msg, messaging_service_sid=from_number, to=phone)
    except Exception:
        pass

def kpi_push(metric, payload):
    try:
        upsert_record("KPI_Log", "key", metric, payload)
    except Exception:
        pass

async def run_rei_dispo():
    phone = os.getenv("ALERT_PHONE")
    while True:
        try:
            deals = []
            csv_url = os.getenv("ZILLOW_CSV_URL")
            if csv_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(csv_url) as resp:
                        if resp.status == 200:
                            csv_text = await resp.text()
                            reader = csv.DictReader(csv_text.splitlines())
                            deals = [row for row in reader]

            new_count = 0
            for deal in deals:
                address = deal.get("Property")
                if not address:
                    continue
                inserted = upsert_record("Leads_REI", "Property", address, deal)
                if inserted:
                    new_count += 1

            if new_count > 0:
                message = f"\U0001f3d8️ REI: {new_count} new leads"
                await send_discord("ops", message)
                if phone:
                    send_sms(phone, message)

            kpi_push("rei_lead", {"count": new_count, "ts": int(time.time())})

        except Exception as e:
            await send_discord("errors", f"⚠️ REI engine error: {e!r}")

        await asyncio.sleep(900)
