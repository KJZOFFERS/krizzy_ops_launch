import threading
from datetime import datetime
from typing import Dict, Any

from job_queue import enqueue_sync_airtable
from utils.airtable_utils import read_records
from utils.discord_utils import post_error, post_ops

# Staging tables
TABLE_INBOUND_REI = "Inbound_REI_Raw"
TABLE_INBOUND_GOVCON = "Inbound_GovCon_Raw"

# Production tables
TABLE_LEADS_REI = "Leads_REI"
TABLE_GOVCON_OPPORTUNITIES = "GovCon Opportunities"

ingest_lock = threading.Lock()


def _safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _ingest_rei_records() -> Dict[str, int]:
    """
    Ingest REI records from Inbound_REI_Raw to Leads_REI.
    Processes records where Status is NEW or ERROR.
    Returns {"processed": int, "errors": int}
    """
    processed = 0
    errors = 0

    try:
        # Treat both NEW and ERROR as ingestable so we can retry failed records
        new_records = read_records(
            TABLE_INBOUND_REI,
            filter_formula="OR({Status}='NEW',{Status}='ERROR')"
        )

        for rec in new_records:
            record_id = rec["id"]
            fields = rec.get("fields", {})

            try:
                # Extract numeric fields
                arv = _safe_float(fields.get("ARV"))
                asking = _safe_float(fields.get("Asking"))
                repairs = _safe_float(fields.get("Repairs"))

                spread = None
                if arv is not None and asking is not None and repairs is not None:
                    spread = arv - asking - repairs

                lead_fields: Dict[str, Any] = {}

                # Direct mappings based on your actual Airtable schema
                # Staging columns (from CSV): Name, Source, External_Id, ARV, Asking, Repairs, Address, ...
                # Leads_REI columns (from CSV): address, ARV, Ask, ..., Ingest_TS, External_Id, Source, Name, Asking, Repairs, Spread, Status, Outbound_Status
                lead_fields["External_Id"] = fields.get("External_Id")
                lead_fields["Source"] = fields.get("Source")
                lead_fields["Name"] = fields.get("Name")
                lead_fields["ARV"] = arv
                lead_fields["Asking"] = asking
                lead_fields["Repairs"] = repairs
                lead_fields["Spread"] = spread

                # Address mapping (staging: "Address" → Leads_REI: "address")
                if "Address" in fields and fields["Address"]:
                    lead_fields["address"] = fields["Address"]

                # Default engine state fields
                lead_fields["Status"] = "NEW"
                lead_fields["Outbound_Status"] = "NOT_CONTACTED"
                lead_fields["Ingest_TS"] = datetime.utcnow().isoformat()

                # Write to production table
                enqueue_sync_airtable(
                    TABLE_LEADS_REI,
                    lead_fields,
                    method="write",
                )

                # Mark staging record as INGESTED (clear old error if any)
                enqueue_sync_airtable(
                    TABLE_INBOUND_REI,
                    {"Status": "INGESTED", "Error_Message": ""},
                    method="update",
                    record_id=record_id,
                )

                processed += 1

            except Exception as e:
                errors += 1
                error_msg = f"{type(e).__name__}: {str(e)}"

                # Mark staging record as ERROR with message
                try:
                    enqueue_sync_airtable(
                        TABLE_INBOUND_REI,
                        {
                            "Status": "ERROR",
                            "Error_Message": error_msg[:500],
                        },
                        method="update",
                        record_id=record_id,
                    )
                except Exception:
                    # Best effort; log to Discord at least
                    pass

                post_error(
                    f"🚨 REI Ingest Error for record {record_id}: {error_msg}"
                )

    except Exception as e:
        post_error(f"🔴 REI Ingest Fatal Error: {type(e).__name__}: {e}")
        errors += 1

    return {"processed": processed, "errors": errors}


def _ingest_govcon_records() -> Dict[str, int]:
    """
    Ingest GovCon records from Inbound_GovCon_Raw to GovCon Opportunities.
    Processes records where Status is NEW or ERROR.
    Returns {"processed": int, "errors": int}
    """
    processed = 0
    errors = 0

    try:
        # Also allow retry of ERROR records for GovCon
        new_records = read_records(
            TABLE_INBOUND_GOVCON,
            filter_formula="OR({Status}='NEW',{Status}='ERROR')"
        )

        for rec in new_records:
            record_id = rec["id"]
            fields = rec.get("fields", {})

            try:
                # Basic field mapping based on the schema we discussed
                opp_fields: Dict[str, Any] = {}

                # Staging expected: External_Id, Source, Solicitation Number, Title, Agency,
                # NAICS, Set_Aside, Response_Deadline, Estimated_Value, Raw_Payload, Status, Error_Message
                # Production: GovCon Opportunities with equivalent fields
                mapping = {
                    "External_Id": "External_Id",
                    "Source": "Source",
                    "Solicitation Number": "Solicitation Number",
                    "Title": "Title",
                    "Agency": "Agency",
                    "NAICS": "NAICS",
                    "Set_Aside": "Set_Aside",
                    "Response_Deadline": "Response_Deadline",
                    "Estimated_Value": "Estimated_Value",
                }

                for src_field, dest_field in mapping.items():
                    if src_field in fields and fields[src_field] is not None:
                        opp_fields[dest_field] = fields[src_field]

                # Default engine fields on clean table
                opp_fields["Status"] = "NEW"

                # Write to production table
                enqueue_sync_airtable(
                    TABLE_GOVCON_OPPORTUNITIES,
                    opp_fields,
                    method="write",
                )

                # Mark staging record as INGESTED
                enqueue_sync_airtable(
                    TABLE_INBOUND_GOVCON,
                    {"Status": "INGESTED", "Error_Message": ""},
                    method="update",
                    record_id=record_id,
                )

                processed += 1

            except Exception as e:
                errors += 1
                error_msg = f"{type(e).__name__}: {str(e)}"

                try:
                    enqueue_sync_airtable(
                        TABLE_INBOUND_GOVCON,
                        {
                            "Status": "ERROR",
                            "Error_Message": error_msg[:500],
                        },
                        method="update",
                        record_id=record_id,
                    )
                except Exception:
                    pass

                post_error(
                    f"🚨 GovCon Ingest Error for record {record_id}: {error_msg}"
                )

    except Exception as e:
        post_error(f"🔴 GovCon Ingest Fatal Error: {type(e).__name__}: {e}")
        errors += 1

    return {"processed": processed, "errors": errors}


def run_ingest_cycle() -> Dict[str, Any]:
    """
    Run a single ingestion cycle for both REI and GovCon.
    Returns summary stats.
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
                f"✅ Ingest Complete: "
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
