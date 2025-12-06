import threading
from typing import Dict, Any
from datetime import datetime

from utils.airtable_utils import read_records, write_record, update_record
from utils.discord_utils import post_error, post_ops

# Staging tables
TABLE_INBOUND_REI = "Inbound_REI_Raw"
TABLE_INBOUND_GOVCON = "Inbound_GovCon_Raw"

# Production tables
TABLE_LEADS_REI = "Leads_REI"
TABLE_GOVCON_OPPORTUNITIES = "GovCon Opportunities"

ingest_lock = threading.Lock()


def _ingest_rei_records() -> Dict[str, int]:
    """
    Ingest REI records from Inbound_REI_Raw to Leads_REI.

    Staging (Inbound_REI_Raw) expected fields:
      External_Id, Source, Name, Phone, Address, City, State, ZIP,
      ARV, Asking, Repairs, Raw_Payload, Status, Error_Message

    Production (Leads_REI) fields we write:
      External_Id, Source, Name, Phone, Address, City, State, ZIP,
      ARV, Asking, Repairs, Spread, Status, Outbound_Status, Ingest_TS
      (and also old 'address' field for compatibility)
    """
    processed = 0
    errors = 0

    try:
        new_records = read_records(
            TABLE_INBOUND_REI,
            filter_formula="{Status}='NEW'"
        )

        for rec in new_records:
            record_id = rec.get("id")
            fields = rec.get("fields", {}) or {}

            try:
                lead_fields: Dict[str, Any] = {}

                # 1:1 mappings from staging to production (new schema)
                copy_keys = [
                    "External_Id",
                    "Source",
                    "Name",
                    "Phone",
                    "Address",
                    "City",
                    "State",
                    "ZIP",
                    "ARV",
                    "Asking",
                    "Repairs",
                ]
                for key in copy_keys:
                    value = fields.get(key)
                    if value not in (None, ""):
                        lead_fields[key] = value

                # Also map Address -> old 'address' field for compatibility
                if fields.get("Address"):
                    lead_fields["address"] = fields["Address"]

                # Compute Spread if numbers are present
                arv = fields.get("ARV")
                asking = fields.get("Asking")
                repairs = fields.get("Repairs")
                try:
                    if arv is not None and asking is not None and repairs is not None:
                        spread = float(arv) - float(asking) - float(repairs)
                        lead_fields["Spread"] = spread
                except Exception:
                    # If casting fails, ignore and leave Spread empty
                    pass

                # Lifecycle fields
                lead_fields["Status"] = "NEW"
                lead_fields["Outbound_Status"] = "NOT_CONTACTED"
                lead_fields["Ingest_TS"] = datetime.utcnow().isoformat()

                # Write into Leads_REI
                write_record(TABLE_LEADS_REI, lead_fields)

                # Mark staging record as INGESTED
                update_record(
                    TABLE_INBOUND_REI,
                    record_id,
                    {"Status": "INGESTED", "Error_Message": ""}
                )

                processed += 1

            except Exception as e:
                errors += 1
                error_msg = f"{type(e).__name__}: {e}"

                # Mark staging record as ERROR (best effort)
                try:
                    update_record(
                        TABLE_INBOUND_REI,
                        record_id,
                        {
                            "Status": "ERROR",
                            "Error_Message": error_msg[:500],
                        },
                    )
                except Exception:
                    pass

                post_error(f"🚨 REI Ingest Error for record {record_id}: {error_msg}")

    except Exception as e:
        post_error(f"🔴 REI Ingest Fatal Error: {type(e).__name__}: {e}")
        errors += 1

    return {"processed": processed, "errors": errors}


def _ingest_govcon_records() -> Dict[str, int]:
    """
    Ingest GovCon records from Inbound_GovCon_Raw to GovCon Opportunities.

    Staging (Inbound_GovCon_Raw) expected fields:
      External_Id, Source, Solicitation Number, Title, Agency,
      NAICS, Set_Aside, Response_Deadline, Estimated_Value,
      Raw_Payload, Status, Error_Message

    Production (GovCon Opportunities) fields we write:
      External_Id, Source, Solicitation Number, Title, Agency,
      NAICS, Set_Aside, Response_Deadline, Estimated_Value, Status
    """
    processed = 0
    errors = 0

    try:
        new_records = read_records(
            TABLE_INBOUND_GOVCON,
            filter_formula="{Status}='NEW'"
        )

        for rec in new_records:
            record_id = rec.get("id")
            fields = rec.get("fields", {}) or {}

            try:
                opp_fields: Dict[str, Any] = {}

                copy_keys = [
                    "External_Id",
                    "Source",
                    "Solicitation Number",
                    "Title",
                    "Agency",
                    "NAICS",
                    "Set_Aside",
                    "Response_Deadline",
                    "Estimated_Value",
                ]
                for key in copy_keys:
                    value = fields.get(key)
                    if value not in (None, ""):
                        opp_fields[key] = value

                # Lifecycle field
                opp_fields["Status"] = "NEW"

                # Write into GovCon Opportunities
                write_record(TABLE_GOVCON_OPPORTUNITIES, opp_fields)

                # Mark staging record as INGESTED
                update_record(
                    TABLE_INBOUND_GOVCON,
                    record_id,
                    {"Status": "INGESTED", "Error_Message": ""}
                )

                processed += 1

            except Exception as e:
                errors += 1
                error_msg = f"{type(e).__name__}: {e}"

                # Mark staging record as ERROR (best effort)
                try:
                    update_record(
                        TABLE_INBOUND_GOVCON,
                        record_id,
                        {
                            "Status": "ERROR",
                            "Error_Message": error_msg[:500],
                        },
                    )
                except Exception:
                    pass

                post_error(f"🚨 GovCon Ingest Error for record {record_id}: {error_msg}")

    except Exception as e:
        post_error(f"🔴 GovCon Ingest Fatal Error: {type(e).__name__}: {e}")
        errors += 1

    return {"processed": processed, "errors": errors}


def run_ingest_cycle() -> Dict[str, Any]:
    """
    Run a single ingestion cycle for both REI and GovCon.
    Thread-safe via ingest_lock.
    """
    if not ingest_lock.acquire(blocking=False):
        return {
            "status": "running",
            "message": "Ingest already in progress",
        }

    try:
        rei_stats = _ingest_rei_records()
        govcon_stats = _ingest_govcon_records()

        total_processed = rei_stats["processed"] + govcon_stats["processed"]
        total_errors = rei_stats["errors"] + govcon_stats["errors"]

        if total_processed > 0 or total_errors > 0:
            post_ops(
                "✅ Ingest Complete: "
                f"REI={rei_stats['processed']}/{rei_stats['errors']}, "
                f"GovCon={govcon_stats['processed']}/{govcon_stats['errors']}"
            )

        return {
            "status": "ok",
            "ingest_processed": total_processed,
            "errors": total_errors,
            "rei": rei_stats,
            "govcon": govcon_stats,
        }

    finally:
        ingest_lock.release()
