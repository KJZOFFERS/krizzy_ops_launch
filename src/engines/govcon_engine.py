# src/engines/govcon_engine.py
# GovCon Sub-Trap Engine - Full Production Loop
#
# REQUIRED AIRTABLE FIELDS:
# --------------------------
# GovCon_Opportunities:
#   - Title (text)
#   - NAICS (text)
#   - NAICS_Match (checkbox)
#   - Value (number)
#   - Complexity (number, 1-5)
#   - Competition (number, 1-10)
#   - Status (single select: NEW, SCANNED, BID_READY, PASSED)
#   - Score (number)
#   - BidReady (checkbox)
#   - BidSummary (long text)
#   - Link (URL, optional)
#
# KPI_Log:
#   - Engine (text)
#   - Timestamp (text)
#   - Stats (long text)

import datetime
from typing import Dict, Any, Optional, List

# Constants
BID_READY_THRESHOLD = 65


def score_govcon_opp(fields: Dict[str, Any]) -> float:
    """
    Score a GovCon opportunity.
    
    Weights:
    - NAICS Match: 40%
    - Value Score: 30% (scales to $50k = 100)
    - Complexity Score: 20% (lower = better)
    - Competition Score: 10% (lower = better)
    """
    naics_match = 100 if fields.get("NAICS_Match") else 0
    value = fields.get("Value") or 0
    complexity = fields.get("Complexity") or 1
    competition = fields.get("Competition") or 1

    value_score = min(100, (value / 50000) * 100)
    complexity_score = max(0, 100 - (complexity * 20))
    competition_score = max(0, 100 - (competition * 15))

    final = (
        naics_match * 0.4 +
        value_score * 0.3 +
        complexity_score * 0.2 +
        competition_score * 0.1
    )

    return round(final, 2)


def generate_bid_summary(fields: Dict[str, Any], score: float) -> str:
    """
    Generate a short bid summary for high-score opportunities.
    """
    title = fields.get("Title", "Untitled")
    naics = fields.get("NAICS", "N/A")
    value = fields.get("Value") or 0
    complexity = fields.get("Complexity") or 0
    competition = fields.get("Competition") or 0

    summary = (
        f"BID RECOMMENDED | Score: {score}\n"
        f"Title: {title}\n"
        f"NAICS: {naics} | Value: ${value:,.0f}\n"
        f"Complexity: {complexity}/5 | Competition: {competition}/10"
    )
    return summary


async def run_govcon_engine(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    GovCon Sub-Trap Engine - processes government contract opportunities.
    
    Flow:
    1. Fetch opportunities with Status in NEW, SCANNED
    2. Score each opportunity
    3. Update Airtable with Score, Status, BidReady, BidSummary
    4. Send Discord alerts for BidReady opportunities
    5. Log KPIs
    
    Never raises exceptions to FastAPI - always returns JSON.
    """
    from src.common.airtable_client import get_airtable
    from src.common.discord_notify import notify_ops, notify_error

    if payload is None:
        payload = {}

    errors: List[str] = []
    processed = 0
    bid_ready_count = 0
    total_value = 0
    score_sum = 0.0

    # Initialize Airtable
    airtable = get_airtable()
    if airtable is None:
        msg = "Airtable not configured"
        notify_error(f"🚨 GovCon Engine: {msg}")
        return {"status": "error", "engine": "GOVCON_SUBTRAP", "error": msg}

    try:
        # 1. Fetch opportunities to process
        filter_formula = "OR({Status}='NEW',{Status}='SCANNED')"
        opportunities = await airtable.get_all("GovCon_Opportunities", filter_formula=filter_formula)

        if not opportunities:
            notify_ops("📄 GovCon Engine | No opportunities to process")
            return {
                "status": "ok",
                "engine": "GOVCON_SUBTRAP",
                "processed": 0,
                "bid_ready": 0,
                "errors": []
            }

        # 2. Process each opportunity
        for opp in opportunities:
            record_id = opp.get("id")
            fields = opp.get("fields", {})

            # Score the opportunity
            score = score_govcon_opp(fields)
            score_sum += score
            value = fields.get("Value") or 0
            total_value += value

            # Determine status and bid readiness
            is_bid_ready = score >= BID_READY_THRESHOLD
            new_status = "BID_READY" if is_bid_ready else "SCANNED"

            update_fields: Dict[str, Any] = {
                "Score": score,
                "Status": new_status,
                "BidReady": is_bid_ready
            }

            if is_bid_ready:
                bid_ready_count += 1
                update_fields["BidSummary"] = generate_bid_summary(fields, score)

                # Discord alert for bid-ready opportunity
                title = fields.get("Title", "Untitled")
                naics = fields.get("NAICS", "N/A")
                link = fields.get("Link", "")

                alert_msg = (
                    f"🎯 BID READY OPPORTUNITY\n"
                    f"Title: {title}\n"
                    f"NAICS: {naics}\n"
                    f"Value: ${value:,.0f}\n"
                    f"Score: {score}"
                )
                if link:
                    alert_msg += f"\nLink: {link}"

                notify_ops(alert_msg)

            # Update Airtable
            try:
                await airtable.update("GovCon_Opportunities", record_id, update_fields)
                processed += 1
            except Exception as e:
                errors.append(f"Update failed for {record_id}: {e}")

        # 3. Log KPIs
        avg_score = round(score_sum / processed, 2) if processed > 0 else 0

        kpi_stats = {
            "processed": processed,
            "bid_ready": bid_ready_count,
            "total_value": total_value,
            "avg_score": avg_score,
            "errors": len(errors)
        }

        try:
            await airtable.create("KPI_Log", {
                "Engine": "GOVCON_SUBTRAP",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
                "Stats": str(kpi_stats)
            })
        except Exception as e:
            errors.append(f"KPI log failed: {e}")

        # 4. Final Discord summary
        summary = (
            f"📄 GovCon Engine Complete\n"
            f"Processed: {processed} | Bid Ready: {bid_ready_count}\n"
            f"Total Value: ${total_value:,.0f} | Avg Score: {avg_score}"
        )
        if errors:
            summary += f"\n⚠️ Errors: {len(errors)}"
        notify_ops(summary)

        return {
            "status": "ok",
            "engine": "GOVCON_SUBTRAP",
            "processed": processed,
            "bid_ready": bid_ready_count,
            "total_value": total_value,
            "avg_score": avg_score,
            "errors": errors
        }

    except Exception as e:
        notify_error(f"🚨 GovCon Engine CRASHED: {e}")
        return {
            "status": "error",
            "engine": "GOVCON_SUBTRAP",
            "error": str(e),
            "errors": errors
        }
```

---

## APP WIRING

**No changes needed to `src/app.py`** — it already imports `run_rei_engine` and `run_govcon_engine` as functions, which the new files export correctly.

---

## VERIFY

After deploying:

**1. Test REI Engine:**
```
GET https://krizzyopslaunch-production.up.railway.app/rei
