# src/engines/rei_engine.py
# REI Dispo Engine - Full Production Loop
#
# REQUIRED AIRTABLE FIELDS:
# --------------------------
# Leads_REI:
#   - Address (text)
#   - Zip (text)
#   - ARV (number)
#   - Asking (number)
#   - Repairs (number)
#   - LocationScore (number, 0-100)
#   - Status (single select: NEW, FOLLOW_UP, SCORED, CONTACTED, CLOSED)
#   - Score (number)
#   - Spread (number)
#   - KRIZZY_Share (number)
#   - OwnerPhone (text, optional)
#
# Buyers:
#   - Name (text)
#   - Phone (text)
#   - MaxPrice (number)
#   - Zones (text, comma-separated zips)
#   - Liquidity (number)
#   - Active (checkbox)
#
# KPI_Log:
#   - Engine (text)
#   - Timestamp (text)
#   - Stats (long text)

import os
import datetime
from typing import Dict, Any, Optional, List

# Constants
HIGH_SCORE_THRESHOLD = 65
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER")


def score_rei_lead(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a lead and compute derived fields.
    Returns dict with: score, spread, krizzy_share
    """
    arv = fields.get("ARV") or 0
    asking = fields.get("Asking") or 0
    repairs = fields.get("Repairs") or 0
    loc_score = fields.get("LocationScore") or 0

    if not arv or not asking:
        return {"score": 0, "spread": 0, "krizzy_share": 0}

    spread = arv - asking - repairs
    spread_pct = (spread / arv) * 100 if arv > 0 else 0
    spread_score = max(0, min(100, spread_pct))
    loc_score_clamped = max(0, min(100, loc_score))

    final_score = round((spread_score * 0.7) + (loc_score_clamped * 0.3), 2)
    krizzy_share = round(spread * 0.05, 2) if spread > 0 else 0

    return {
        "score": final_score,
        "spread": round(spread, 2),
        "krizzy_share": krizzy_share
    }


def match_buyers(lead_fields: Dict[str, Any], buyers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Match a lead to eligible buyers based on price, zones, and liquidity.
    """
    arv = lead_fields.get("ARV") or 0
    lead_zip = str(lead_fields.get("Zip") or "").strip()

    matched = []
    for buyer in buyers:
        bf = buyer.get("fields", {})

        if not bf.get("Active"):
            continue

        max_price = bf.get("MaxPrice") or 0
        zones_raw = bf.get("Zones") or ""
        zones = [z.strip() for z in zones_raw.split(",") if z.strip()]
        liquidity = bf.get("Liquidity") or 0

        # Match criteria
        if arv <= max_price and lead_zip in zones and liquidity >= arv * 0.2:
            matched.append(buyer)

    return matched


async def run_rei_engine(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    REI Dispo Engine - processes real estate leads from Airtable.
    
    Flow:
    1. Fetch active leads (Status in NEW, FOLLOW_UP)
    2. Score each lead
    3. Update Airtable with Score, Spread, KRIZZY_Share, Status
    4. Match high-score leads to buyers
    5. Send SMS to matched buyers (if Twilio configured)
    6. Send Discord summary
    7. Log KPIs
    
    Never raises exceptions to FastAPI - always returns JSON.
    """
    from src.common.airtable_client import get_airtable
    from src.common.discord_notify import notify_ops, notify_error
    from src.common.twilio_client import get_twilio

    if payload is None:
        payload = {}

    errors: List[str] = []
    leads_processed = 0
    high_score_count = 0
    sms_sent = 0
    buyers_matched = 0

    # Initialize Airtable
    airtable = get_airtable()
    if airtable is None:
        msg = "Airtable not configured"
        notify_error(f"🚨 REI Engine: {msg}")
        return {"status": "error", "engine": "REI_DISPO", "error": msg}

    # Initialize Twilio (optional)
    twilio_client = get_twilio()

    try:
        # 1. Fetch active leads
        filter_formula = "OR({Status}='NEW',{Status}='FOLLOW_UP')"
        leads = await airtable.get_all("Leads_REI", filter_formula=filter_formula)

        if not leads:
            notify_ops("🏠 REI Engine | No active leads to process")
            return {
                "status": "ok",
                "engine": "REI_DISPO",
                "leads_processed": 0,
                "high_score": 0,
                "sms_sent": 0,
                "errors": []
            }

        # 2. Fetch buyers for matching
        buyers = []
        try:
            buyers = await airtable.get_all("Buyers", filter_formula="{Active}=TRUE()")
        except Exception as e:
            errors.append(f"Buyers fetch failed: {e}")

        # 3. Process each lead
        high_score_leads: List[Dict[str, Any]] = []

        for lead in leads:
            record_id = lead.get("id")
            fields = lead.get("fields", {})

            # Score the lead
            scoring = score_rei_lead(fields)
            score = scoring["score"]
            spread = scoring["spread"]
            krizzy_share = scoring["krizzy_share"]

            # Determine new status
            new_status = "SCORED"
            if score >= HIGH_SCORE_THRESHOLD:
                high_score_count += 1
                high_score_leads.append({
                    "id": record_id,
                    "fields": fields,
                    "score": score,
                    "spread": spread
                })

            # Update Airtable
            update_fields = {
                "Score": score,
                "Spread": spread,
                "KRIZZY_Share": krizzy_share,
                "Status": new_status
            }

            try:
                await airtable.update("Leads_REI", record_id, update_fields)
                leads_processed += 1
            except Exception as e:
                errors.append(f"Update failed for {record_id}: {e}")

        # 4. Match buyers and send SMS for high-score leads
        for hs_lead in high_score_leads:
            lead_fields = hs_lead["fields"]
            lead_id = hs_lead["id"]
            score = hs_lead["score"]
            spread = hs_lead["spread"]

            matched = match_buyers(lead_fields, buyers)
            buyers_matched += len(matched)

            address = lead_fields.get("Address", "Unknown")

            # Send Discord alert for high-score deal
            deal_msg = (
                f"🔥 HIGH-SCORE DEAL\n"
                f"Address: {address}\n"
                f"ARV: ${lead_fields.get('ARV', 0):,.0f}\n"
                f"Asking: ${lead_fields.get('Asking', 0):,.0f}\n"
                f"Spread: ${spread:,.0f}\n"
                f"Score: {score}\n"
                f"Matched Buyers: {len(matched)}"
            )
            notify_ops(deal_msg)

            # Send SMS to matched buyers
            if twilio_client and TWILIO_FROM and matched:
                for buyer in matched:
                    bf = buyer.get("fields", {})
                    phone = bf.get("Phone")
                    name = bf.get("Name", "Investor")

                    if not phone:
                        continue

                    sms_body = (
                        f"KRIZZY OPS: New deal alert!\n"
                        f"{address}\n"
                        f"ARV: ${lead_fields.get('ARV', 0):,.0f}\n"
                        f"Spread: ${spread:,.0f}\n"
                        f"Reply YES if interested."
                    )

                    try:
                        twilio_client.messages.create(
                            body=sms_body,
                            from_=TWILIO_FROM,
                            to=phone
                        )
                        sms_sent += 1
                    except Exception as e:
                        errors.append(f"SMS to {phone} failed: {e}")

                # Update lead status to CONTACTED if SMS sent
                if sms_sent > 0:
                    try:
                        await airtable.update("Leads_REI", lead_id, {"Status": "CONTACTED"})
                    except Exception as e:
                        errors.append(f"Status update to CONTACTED failed: {e}")

        # 5. Log KPIs
        kpi_stats = {
            "leads_processed": leads_processed,
            "high_score": high_score_count,
            "buyers_matched": buyers_matched,
            "sms_sent": sms_sent,
            "errors": len(errors)
        }

        try:
            await airtable.create("KPI_Log", {
                "Engine": "REI_DISPO",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
                "Stats": str(kpi_stats)
            })
        except Exception as e:
            errors.append(f"KPI log failed: {e}")

        # 6. Final Discord summary
        summary = (
            f"🏠 REI Engine Complete\n"
            f"Leads: {leads_processed} | High-Score: {high_score_count}\n"
            f"Buyers Matched: {buyers_matched} | SMS Sent: {sms_sent}"
        )
        if errors:
            summary += f"\n⚠️ Errors: {len(errors)}"
        notify_ops(summary)

        return {
            "status": "ok",
            "engine": "REI_DISPO",
            "leads_processed": leads_processed,
            "high_score": high_score_count,
            "buyers_matched": buyers_matched,
            "sms_sent": sms_sent,
            "errors": errors
        }

    except Exception as e:
        notify_error(f"🚨 REI Engine CRASHED: {e}")
        return {
            "status": "error",
            "engine": "REI_DISPO",
            "error": str(e),
            "errors": errors
        }
