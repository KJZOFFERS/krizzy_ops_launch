import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from app_v2 import config
from app_v2.models.deal import Deal
from app_v2.models.system_state import system_state
from app_v2.utils import airtable_client
from app_v2.utils.discord_client import post_ops, post_error
from app_v2.utils.logger import get_logger, log_engine_cycle, log_error

logger = get_logger(__name__)


class InputEngine:
    """
    24/7 Lead Ingestion Engine

    Responsibilities:
    - Pull leads from multiple sources (Gmail, staging tables, webhooks)
    - Normalize raw payloads into structured Deal objects
    - Validate and pre-score deals
    - Insert into Inbound_REI_Raw for underwriting
    - Track inbound velocity for dynamic orchestration
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.leads_ingested_last_hour = 0
        self.last_velocity_reset = datetime.utcnow()

    def parse_raw_payload(self, raw_payload: str) -> Optional[Dict[str, Any]]:
        """
        Parse raw JSON payload from various sources.
        Returns structured dict or None if invalid.
        """
        try:
            if not raw_payload or not raw_payload.strip():
                return None

            # Try parsing as JSON
            data = json.loads(raw_payload)

            # Basic validation
            if not isinstance(data, dict):
                return None

            return data

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse raw payload: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing payload: {e}")
            return None

    def normalize_lead(self, raw_data: Dict[str, Any]) -> Optional[Deal]:
        """
        Normalize raw lead data into Deal object.
        Handles various input formats and field name variations.
        """
        try:
            # Extract address fields (handle variations)
            address = raw_data.get("address") or raw_data.get("Address") or ""
            city = raw_data.get("city") or raw_data.get("City") or ""
            state = raw_data.get("state") or raw_data.get("State") or ""
            zip_code = raw_data.get("zip") or raw_data.get("ZIP") or raw_data.get("zip_code") or ""

            # Extract financial fields (handle variations)
            arv = None
            asking = None
            repairs = None

            # ARV
            arv_raw = raw_data.get("arv") or raw_data.get("ARV")
            if arv_raw is not None:
                try:
                    arv = float(arv_raw)
                except (ValueError, TypeError):
                    pass

            # Asking price
            asking_raw = (
                raw_data.get("asking") or
                raw_data.get("Asking") or
                raw_data.get("ask") or
                raw_data.get("Ask")
            )
            if asking_raw is not None:
                try:
                    asking = float(asking_raw)
                except (ValueError, TypeError):
                    pass

            # Repairs
            repairs_raw = raw_data.get("repairs") or raw_data.get("Repairs")
            if repairs_raw is not None:
                try:
                    repairs = float(repairs_raw)
                except (ValueError, TypeError):
                    pass

            # Extract metadata
            source = raw_data.get("source") or raw_data.get("Source") or "UNKNOWN"
            external_id = raw_data.get("external_id") or raw_data.get("External_Id") or f"INPUT_{int(time.time())}"
            seller_name = raw_data.get("name") or raw_data.get("Name") or raw_data.get("seller_name")

            # Validation: Must have at least address and one financial field
            if not address and not city:
                self.logger.warning(f"Lead missing address: {external_id}")
                return None

            if arv is None and asking is None:
                self.logger.warning(f"Lead missing financial data: {external_id}")
                return None

            # Create Deal object
            deal = Deal(
                external_id=external_id,
                source=source,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                arv=arv,
                asking=asking,
                repairs=repairs if repairs is not None else 0.0,
                seller_name=seller_name,
                raw_payload=json.dumps(raw_data),
                status="NEW",
                created_at=datetime.utcnow(),
            )

            return deal

        except Exception as e:
            log_error(self.logger, "Failed to normalize lead", e)
            return None

    def pre_score_lead(self, deal: Deal) -> bool:
        """
        Quick pre-screening to filter out obvious trash before underwriting.
        Returns True if lead should be ingested, False if rejected.
        """
        try:
            # Reject if no ARV
            if not deal.arv or deal.arv <= 0:
                self.logger.debug(f"Rejected {deal.external_id}: Invalid ARV")
                return False

            # Reject if ARV is unrealistically low
            if deal.arv < 20000:
                self.logger.debug(f"Rejected {deal.external_id}: ARV too low (${deal.arv})")
                return False

            # Reject if asking exceeds ARV by more than 50% (likely data error)
            if deal.asking and deal.asking > deal.arv * 1.5:
                self.logger.debug(f"Rejected {deal.external_id}: Asking far exceeds ARV")
                return False

            # Reject if repairs exceed ARV (likely data error)
            if deal.repairs and deal.repairs > deal.arv:
                self.logger.debug(f"Rejected {deal.external_id}: Repairs exceed ARV")
                return False

            # Accept all other leads for full underwriting
            return True

        except Exception as e:
            log_error(self.logger, f"Pre-score failed for {deal.external_id}", e)
            return False

    def ingest_from_staging(self) -> int:
        """
        Pull NEW records from Inbound_REI_Raw that were created externally
        (e.g., via data feed engine or manual entry).
        Returns count of leads processed.
        """
        processed = 0

        try:
            # Read records with Status=NEW and no Raw_Payload (external source)
            records = airtable_client.read_records(
                config.TABLE_INBOUND_REI,
                filter_formula="AND({Status}='NEW', {Raw_Payload}='')"
            )

            for record in records:
                try:
                    fields = record.get("fields", {})
                    record_id = record["id"]

                    # Build raw_data dict from Airtable fields
                    raw_data = {
                        "external_id": fields.get("External_Id"),
                        "source": fields.get("Source", "STAGING"),
                        "address": fields.get("Address"),
                        "city": fields.get("City"),
                        "state": fields.get("State"),
                        "zip": fields.get("ZIP"),
                        "arv": fields.get("ARV"),
                        "asking": fields.get("Asking"),
                        "repairs": fields.get("Repairs"),
                        "name": fields.get("Name"),
                    }

                    # Normalize
                    deal = self.normalize_lead(raw_data)
                    if not deal:
                        # Mark as ERROR
                        airtable_client.update_record(
                            config.TABLE_INBOUND_REI,
                            record_id,
                            {
                                "Status": "ERROR",
                                "Error_Message": "Failed to normalize lead"
                            }
                        )
                        continue

                    # Pre-score
                    if not self.pre_score_lead(deal):
                        # Mark as REJECTED
                        airtable_client.update_record(
                            config.TABLE_INBOUND_REI,
                            record_id,
                            {
                                "Status": "REJECTED",
                                "Error_Message": "Failed pre-screening"
                            }
                        )
                        continue

                    # Update record with normalized data + Raw_Payload
                    airtable_client.update_record(
                        config.TABLE_INBOUND_REI,
                        record_id,
                        {
                            "Raw_Payload": deal.raw_payload,
                            "Status": "NEW"  # Keep as NEW for underwriting
                        }
                    )

                    processed += 1
                    self.leads_ingested_last_hour += 1

                except Exception as e:
                    log_error(self.logger, f"Failed to process staging record {record.get('id')}", e)

        except Exception as e:
            log_error(self.logger, "Failed to ingest from staging", e)

        return processed

    def ingest_from_gmail(self) -> int:
        """
        Pull JV deals from Gmail (label: JV_Deals).
        TODO: Implement when gmail_client.py is ready.
        Returns count of leads processed.
        """
        # Placeholder until gmail_client is implemented
        # When ready:
        # 1. Pull messages with label JV_Deals
        # 2. Parse body text for deal info (address, ARV, asking, etc.)
        # 3. Normalize into Deal objects
        # 4. Write to Inbound_REI_Raw
        return 0

    def update_velocity_metrics(self):
        """Update system state with inbound velocity for orchestrator"""
        now = datetime.utcnow()
        elapsed_seconds = (now - self.last_velocity_reset).total_seconds()

        # Reset counter every hour
        if elapsed_seconds >= 3600:
            system_state.inbound_velocity_last_hour = self.leads_ingested_last_hour
            self.logger.info(f"Inbound velocity: {self.leads_ingested_last_hour} leads/hour")

            # Reset
            self.leads_ingested_last_hour = 0
            self.last_velocity_reset = now

    def run_input_cycle(self) -> Dict[str, int]:
        """
        Single input cycle:
        1. Ingest from staging
        2. Ingest from Gmail (TODO)
        3. Update velocity metrics
        """
        start_time = time.time()
        total_processed = 0
        errors = 0

        try:
            # Ingest from staging table
            staging_count = self.ingest_from_staging()
            total_processed += staging_count

            # Ingest from Gmail (TODO: implement when gmail_client ready)
            # gmail_count = self.ingest_from_gmail()
            # total_processed += gmail_count

            # Update velocity
            self.update_velocity_metrics()

        except Exception as e:
            errors += 1
            log_error(self.logger, "Input cycle failed", e)
            post_error(f"🚨 Input Engine Cycle Error: {type(e).__name__}: {e}")

        duration = time.time() - start_time
        log_engine_cycle(self.logger, "INPUT", total_processed, errors, duration)

        return {"processed": total_processed, "errors": errors}

    def start(self):
        """Main input engine loop (24/7)"""
        self.logger.info("Input Engine started")
        post_ops("🟢 Input Engine started")

        while True:
            try:
                # Get dynamic interval
                interval = system_state.get_engine_interval("input")

                # Run cycle
                result = self.run_input_cycle()

                # Record run
                system_state.record_engine_run(
                    "input",
                    success=result["errors"] == 0
                )

                # Sleep until next cycle
                time.sleep(interval)

            except Exception as e:
                log_error(self.logger, "Input loop critical error", e)
                system_state.record_engine_run("input", success=False, error=str(e))
                post_error(f"🔴 Input Engine Critical Error: {type(e).__name__}: {e}")
                time.sleep(60)  # Fallback interval


def input_loop():
    """Entry point for thread supervisor"""
    engine = InputEngine()
    engine.start()
