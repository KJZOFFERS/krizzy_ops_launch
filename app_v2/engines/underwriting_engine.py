import time
from typing import List
from app_v2 import config
from app_v2.models.deal import Deal
from app_v2.models.system_state import system_state
from app_v2.utils import airtable_client
from app_v2.utils import scoring_utils
from app_v2.utils.discord_client import post_deal_alert
from app_v2.utils.logger import get_logger, log_engine_cycle, log_error

logger = get_logger(__name__)


def process_deal(deal: Deal) -> bool:
    """
    Underwrite a single deal: compute MAO, spread, strategy
    Returns True if successful
    """
    try:
        # Validate required fields
        if not deal.arv or not deal.asking or deal.repairs is None:
            logger.warning(f"Deal {deal.external_id} missing required fields")
            return False

        # Compute metrics
        deal.mao = scoring_utils.compute_mao(deal.arv, deal.repairs)
        deal.spread = scoring_utils.compute_spread(deal.arv, deal.asking, deal.repairs)
        deal.spread_ratio = scoring_utils.compute_spread_ratio(deal.arv, deal.spread)

        # Score equity
        deal.equity_score, deal.strategy, deal.risk_flags = scoring_utils.score_equity(
            deal.arv, deal.asking, deal.repairs
        )

        # Update status
        deal.status = "UNDERWRITTEN"

        # Write to Leads_REI
        fields = deal.to_airtable_fields()
        fields["Spread"] = deal.spread
        fields["Status"] = "UNDERWRITTEN"

        airtable_client.write_record(config.TABLE_LEADS_REI, fields)

        # Alert if high-value deal
        if deal.spread and deal.spread >= config.HIGH_POTENTIAL_SPREAD:
            post_deal_alert(deal.address, deal.spread, deal.arv, deal.asking)

        logger.info(
            f"Underwritten deal {deal.external_id}: "
            f"spread=${deal.spread:,.0f}, strategy={deal.strategy}"
        )

        return True

    except Exception as e:
        log_error(logger, f"Failed to underwrite deal {deal.external_id}", e)
        return False


def run_underwriting_cycle() -> dict:
    """
    Single underwriting cycle:
    1. Pull NEW deals from Inbound_REI_Raw
    2. Compute MAO, spread, strategy
    3. Write to Leads_REI
    """
    processed = 0
    errors = 0
    start_time = time.time()

    try:
        # Get NEW deals that haven't been underwritten
        records = airtable_client.read_records(
            config.TABLE_INBOUND_REI,
            filter_formula="{Status}='NEW'"
        )

        for record in records:
            try:
                # Parse deal
                fields = record.get("fields", {})
                deal = Deal(
                    external_id=fields.get("External_Id", record["id"]),
                    source=fields.get("Source", "UNKNOWN"),
                    address=fields.get("Address", ""),
                    city=fields.get("City", ""),
                    state=fields.get("State", ""),
                    zip_code=fields.get("ZIP", ""),
                    arv=fields.get("ARV"),
                    asking=fields.get("Asking"),
                    repairs=fields.get("Repairs"),
                    seller_name=fields.get("Name"),
                    raw_payload=fields.get("Raw_Payload"),
                )

                # Underwrite
                if process_deal(deal):
                    # Mark staging as UNDERWRITTEN
                    airtable_client.update_record(
                        config.TABLE_INBOUND_REI,
                        record["id"],
                        {"Status": "UNDERWRITTEN"}
                    )
                    processed += 1
                else:
                    errors += 1

            except Exception as e:
                errors += 1
                log_error(logger, f"Error processing record {record.get('id')}", e)

    except Exception as e:
        errors += 1
        log_error(logger, "Underwriting cycle failed", e)

    duration = time.time() - start_time
    log_engine_cycle(logger, "UNDERWRITING", processed, errors, duration)

    return {"processed": processed, "errors": errors}


def underwriting_loop():
    """Main underwriting engine loop"""
    logger.info("Underwriting engine started")

    while True:
        try:
            interval = system_state.get_engine_interval("underwriting")
            result = run_underwriting_cycle()

            system_state.record_engine_run(
                "underwriting",
                success=result["errors"] == 0
            )

            time.sleep(interval)

        except Exception as e:
            log_error(logger, "Underwriting loop error", e)
            system_state.record_engine_run("underwriting", success=False, error=str(e))
            time.sleep(60)
