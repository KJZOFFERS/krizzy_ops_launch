#!/usr/bin/env python3
"""
krizzy_bots.py

Single-file implementation of KRIZZY OPS bots:
- REI_DISPO_ENGINE (real estate dispo: leads → SMS → deals)
- GOVCON_SUBTRAP_ENGINE (GovCon: opportunities → digest → bids)

Relies only on:
- Python 3.10+ standard library
- Live HTTP access to Airtable, Twilio, Discord, SAM.gov, and a user-configured free REI feed.
"""

import base64
import csv
import datetime
import io
import json
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple
import http.client
import ssl
import urllib.parse


# ---------------------------------------------------------------------------
# Config / Environment helpers
# ---------------------------------------------------------------------------


def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def require_env_var(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"MISSING_INPUT: environment variable {name} is required but not set")
    return value


def get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# Generic HTTP helpers
# ---------------------------------------------------------------------------


def http_request_raw(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: int = 30,
) -> Tuple[int, Dict[str, str], bytes]:
    """
    Low-level HTTP request helper.

    Returns:
        (status_code, response_headers, response_body_bytes)
    Does NOT raise on non-2xx; callers decide how to handle status.
    """
    if headers is None:
        headers = {}
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"Invalid URL: {url}")

    if parsed.scheme == "https":
        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout, context=context)
    else:
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    # Always send a basic User-Agent
    if "User-Agent" not in headers:
        headers["User-Agent"] = "krizzy-bots/1.0"

    conn.request(method.upper(), path, body=body, headers=headers)
    resp = conn.getresponse()
    resp_body = resp.read()
    resp_headers = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return resp.status, resp_headers, resp_body


def http_request_json(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    status, resp_headers, resp_body = http_request_raw(method, url, headers=headers, body=body, timeout=timeout)
    text = resp_body.decode("utf-8", errors="replace") if resp_body else ""
    if status < 200 or status >= 300:
        raise RuntimeError(f"HTTP {status} error for {url}: {text[:500]}")
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON from {url}: {exc}") from exc


def http_request_text(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: int = 30,
) -> str:
    status, resp_headers, resp_body = http_request_raw(method, url, headers=headers, body=body, timeout=timeout)
    text = resp_body.decode("utf-8", errors="replace") if resp_body else ""
    if status < 200 or status >= 300:
        raise RuntimeError(f"HTTP {status} error for {url}: {text[:500]}")
    return text


# ---------------------------------------------------------------------------
# Airtable helpers
# ---------------------------------------------------------------------------


def _airtable_base_url(table_name: str) -> str:
    base_id = require_env_var("AIRTABLE_BASE_ID")
    encoded_table = urllib.parse.quote(table_name, safe="")
    return f"https://api.airtable.com/v0/{base_id}/{encoded_table}"


def airtable_api_request(
    table_name: str,
    method: str,
    payload: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    api_key = require_env_var("AIRTABLE_API_KEY")
    base_url = _airtable_base_url(table_name)
    if query_params:
        # Convert any non-str values using urlencode
        query_str = urllib.parse.urlencode(query_params, doseq=True)
        url = f"{base_url}?{query_str}"
    else:
        url = base_url

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    return http_request_json(method, url, headers=headers, body=body)


def airtable_fetch_records(table_name: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Fetch all records for a table given optional query parameters.
    Handles Airtable pagination via the 'offset' field.
    """
    records: List[Dict[str, Any]] = []
    params = dict(query_params or {})
    while True:
        resp = airtable_api_request(table_name, "GET", query_params=params)
        page_records = resp.get("records", [])
        records.extend(page_records)
        offset = resp.get("offset")
        if not offset:
            break
        params["offset"] = offset
        # Respect maxRecords if set
        max_records_raw = (query_params or {}).get("maxRecords")
        if max_records_raw:
            try:
                max_records = int(max_records_raw)
                if len(records) >= max_records:
                    records = records[:max_records]
                    break
            except ValueError:
                pass
    return records


def _chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def airtable_upsert_records(table_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Upsert helper:
    - Records without 'id' are created via POST.
    - Records with 'id' are updated via PATCH.
    Airtable allows up to 10 records per request; we chunk accordingly.
    """
    created_total: List[Dict[str, Any]] = []
    updated_total: List[Dict[str, Any]] = []

    to_create = [r for r in records if "id" not in r]
    to_update = [r for r in records if "id" in r]

    # Create
    for chunk in _chunk_list(to_create, 10):
        if not chunk:
            continue
        payload = {"records": chunk}
        resp = airtable_api_request(table_name, "POST", payload=payload)
        created_total.extend(resp.get("records", []))

    # Update
    if to_update:
        # Normalize update payload to {"id": ..., "fields": {...}}
        normalized_updates = []
        for r in to_update:
            rid = r.get("id")
            fields = r.get("fields")
            if not rid or not isinstance(fields, dict):
                raise RuntimeError("Invalid record for update: missing 'id' or 'fields'")
            normalized_updates.append({"id": rid, "fields": fields})

        for chunk in _chunk_list(normalized_updates, 10):
            payload = {"records": chunk}
            resp = airtable_api_request(table_name, "PATCH", payload=payload)
            updated_total.extend(resp.get("records", []))

    return {"created": created_total, "updated": updated_total}


# ---------------------------------------------------------------------------
# Discord helpers
# ---------------------------------------------------------------------------


def discord_post_message(webhook_url: str, message: str) -> None:
    """
    Post a simple text message to a Discord webhook.
    """
    if not webhook_url:
        raise RuntimeError("MISSING_INPUT: Discord webhook URL is required for logging")

    # Discord content limit is 2000 chars; keep some headroom.
    if len(message) > 1900:
        message = message[:1900] + "…"

    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    http_request_json("POST", webhook_url, headers=headers, body=json.dumps(payload).encode("utf-8"))


def log_ops(message: str) -> None:
    webhook = require_env_var("DISCORD_WEBHOOK_OPS")
    try:
        discord_post_message(webhook, message)
    except Exception as exc:  # Logging must never crash the main loop
        sys.stderr.write(f"[log_ops error] {exc}\n")


def log_error(message: str, error: Optional[BaseException] = None) -> None:
    webhook_errors = os.environ.get("DISCORD_WEBHOOK_ERRORS") or os.environ.get("DISCORD_WEBHOOK_OPS")
    if not webhook_errors:
        sys.stderr.write(f"[log_error] {message}\n")
        if error:
            traceback.print_exception(error, error, error.__traceback__, file=sys.stderr)
        return

    error_text = message
    if error:
        error_text += f"\nException: {repr(error)}\nTraceback:\n{traceback.format_exc()}"
    try:
        discord_post_message(webhook_errors, error_text)
    except Exception as exc:
        # Last-resort stderr logging
        sys.stderr.write(f"[log_error fallback] {error_text}\n")
        sys.stderr.write(f"[log_error fallback failure] {exc}\n")


# ---------------------------------------------------------------------------
# Twilio helper
# ---------------------------------------------------------------------------


def _twilio_auth_header() -> str:
    account_sid = require_env_var("TWILIO_ACCOUNT_SID")
    auth_token = require_env_var("TWILIO_AUTH_TOKEN")
    token = f"{account_sid}:{auth_token}".encode("utf-8")
    encoded = base64.b64encode(token).decode("ascii")
    return f"Basic {encoded}"


def twilio_send_sms(to_number: str, body: str) -> Dict[str, Any]:
    """
    Send an SMS using Twilio's Messages API and a Messaging Service SID.
    Raises on non-2xx responses.
    """
    if not to_number:
        raise RuntimeError("MISSING_INPUT: to_number is required for twilio_send_sms")

    account_sid = require_env_var("TWILIO_ACCOUNT_SID")
    messaging_service_sid = require_env_var("TWILIO_MESSAGING_SERVICE_SID")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    headers = {
        "Authorization": _twilio_auth_header(),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "To": to_number,
        "MessagingServiceSid": messaging_service_sid,
        "Body": body,
    }
    encoded = urllib.parse.urlencode(payload).encode("utf-8")

    # Twilio returns JSON
    resp = http_request_json("POST", url, headers=headers, body=encoded)
    return {
        "sid": resp.get("sid"),
        "status": resp.get("status"),
        "to": resp.get("to"),
        "raw": resp,
    }


# ---------------------------------------------------------------------------
# KPI + Cracks helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _clean_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys with None values to avoid empty fields in Airtable."""
    return {k: v for k, v in fields.items() if v is not None}


def kpi_log(engine: str, metric: str, value: Any, extra_context: Optional[Dict[str, Any]] = None) -> None:
    fields = {
        "Engine": engine,
        "Metric": metric,
        "Value": value,
        "Timestamp": _now_iso(),
        "ContextJSON": json.dumps(extra_context, default=str) if extra_context is not None else None,
    }
    try:
        airtable_upsert_records("KPI_Log", [{"fields": _clean_fields(fields)}])
    except Exception as exc:
        log_error(f"kpi_log failed for {engine}/{metric}", exc)


def cracks_tracker_log_record(context_type: str, context_payload: Any, error_description: str) -> None:
    fields = {
        "ContextType": context_type,
        "PayloadJSON": json.dumps(context_payload, default=str),
        "ErrorDescription": error_description,
        "Timestamp": _now_iso(),
    }
    try:
        airtable_upsert_records("Cracks_Tracker", [{"fields": _clean_fields(fields)}])
    except Exception as exc:
        log_error("cracks_tracker_log_record failed", exc)


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------


def health_check_airtable() -> Dict[str, Any]:
    try:
        records = airtable_fetch_records("KPI_Log", {"maxRecords": 1})
        ok = True
        detail = f"Fetched {len(records)} KPI_Log record(s)"
    except Exception as exc:
        ok = False
        detail = f"Airtable error: {exc}"
        log_error("health_check_airtable failed", exc)
    return {"ok": ok, "detail": detail}


def health_check_twilio() -> Dict[str, Any]:
    try:
        account_sid = require_env_var("TWILIO_ACCOUNT_SID")
        # Validate we can hit the Account endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
        headers = {
            "Authorization": _twilio_auth_header(),
        }
        status, resp_headers, resp_body = http_request_raw("GET", url, headers=headers)
        text = resp_body.decode("utf-8", errors="replace") if resp_body else ""
        if 200 <= status < 300:
            ok = True
            detail = "Twilio credentials verified via Account endpoint"
        else:
            ok = False
            detail = f"Twilio HTTP {status}: {text[:200]}"
    except Exception as exc:
        ok = False
        detail = f"Twilio health error: {exc}"
        log_error("health_check_twilio failed", exc)
    return {"ok": ok, "detail": detail}


def health_check_discord() -> Dict[str, Any]:
    try:
        webhook = require_env_var("DISCORD_WEBHOOK_OPS")
        test_message = "KRIZZY_OPS health_check ping"
        discord_post_message(webhook, test_message)
        ok = True
        detail = "Discord OPS webhook accepted test message"
    except Exception as exc:
        ok = False
        detail = f"Discord error: {exc}"
        log_error("health_check_discord failed", exc)
    return {"ok": ok, "detail": detail}


def health_check_all() -> Dict[str, Any]:
    airtable_res = health_check_airtable()
    twilio_res = health_check_twilio()
    discord_res = health_check_discord()

    checks = {
        "airtable": airtable_res,
        "twilio": twilio_res,
        "discord": discord_res,
    }
    overall_ok = all(c.get("ok") for c in checks.values())

    status_text = "OK" if overall_ok else "DEGRADED"
    summary = {
        "overall_ok": overall_ok,
        "checks": checks,
    }

    try:
        log_ops(f"[HEALTH_CHECK] overall={status_text} details={json.dumps(checks, default=str)[:1500]}")
        kpi_log("KRIZZY_PLATFORM", "health_check", 1 if overall_ok else 0, extra_context=checks)
    except Exception as exc:
        log_error("health_check_all logging failed", exc)

    return summary


# ---------------------------------------------------------------------------
# REI_DISPO_ENGINE – free/open feed + SMS blast
# ---------------------------------------------------------------------------


def _rei_feed_config_from_env() -> Dict[str, Any]:
    feed_url = get_env("FREE_REI_FEED_URL")
    feed_format = get_env("FREE_REI_FEED_FORMAT", "csv").lower()
    source_name = get_env("FREE_REI_FEED_SOURCE_NAME", "FREE_REI_FEED_URL")
    return {
        "feed_url": feed_url,
        "format": feed_format,
        "source_name": source_name,
    }


def rei_free_feed_fetch_raw_leads(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch raw leads from a user-configured free/open data feed.

    Requirements:
    - config["feed_url"] or FREE_REI_FEED_URL env var must be set to a CSV or JSON URL
      exported from an official open-data portal or your own bulk CSV.
    - For CSV format, expect at minimum a 'Phone' column (case-insensitive).
      Recommended columns (case-insensitive):
        Name, Phone, City, State, Email, Address, Score, Source, Status

    If FREE_REI_FEED_URL is not configured, this function raises:
        RuntimeError("MISSING_INPUT: configure FREE_REI_FEED_URL or set source_config['feed_url'] to a valid open-data CSV/JSON for property/owner leads.")
    """
    feed_url = (config or {}).get("feed_url") or get_env("FREE_REI_FEED_URL")
    feed_format = ((config or {}).get("format") or get_env("FREE_REI_FEED_FORMAT", "csv")).lower()

    if not feed_url:
        raise RuntimeError(
            "MISSING_INPUT: configure FREE_REI_FEED_URL or set source_config['feed_url'] "
            "to a valid open-data CSV/JSON for property/owner leads."
        )

    if feed_format not in ("csv", "json"):
        raise RuntimeError(f"Unsupported FREE_REI_FEED_FORMAT: {feed_format}. Use 'csv' or 'json'.")

    raw_leads: List[Dict[str, Any]] = []

    if feed_format == "csv":
        text = http_request_text("GET", feed_url)
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return []
        fieldnames_lower = [fn.lower() for fn in reader.fieldnames]
        if "phone" not in fieldnames_lower:
            raise RuntimeError(
                "MISSING_INPUT: FREE_REI_FEED_URL must point to a CSV with at least a 'Phone' column."
            )
        for row in reader:
            raw_leads.append(row)
    else:  # json
        data = http_request_json("GET", feed_url)
        if isinstance(data, list):
            raw_leads = [r for r in data if isinstance(r, dict)]
        elif isinstance(data, dict):
            # Common patterns: {"records": [...]} or similar
            if "records" in data and isinstance(data["records"], list):
                raw_leads = [r for r in data["records"] if isinstance(r, dict)]
            else:
                raise RuntimeError(
                    "MISSING_INPUT: JSON feed must be an array of objects or have a top-level 'records' array."
                )
        else:
            raise RuntimeError("MISSING_INPUT: JSON feed must be an array of objects or an object with 'records'.")

    return raw_leads


def _get_first_by_keys(row: Dict[str, Any], keys: List[str]) -> Optional[str]:
    lowered = {k.lower(): v for k, v in row.items()}
    for key in keys:
        if key.lower() in lowered and lowered[key.lower()]:
            return str(lowered[key.lower()])
    return None


def rei_normalize_lead(raw_lead: Dict[str, Any], source: str) -> Dict[str, Any]:
    name = _get_first_by_keys(raw_lead, ["Name", "OwnerName", "Owner", "FullName"])
    phone = _get_first_by_keys(raw_lead, ["Phone", "PhoneNumber", "OwnerPhone", "Phone1"])
    city = _get_first_by_keys(raw_lead, ["City", "MailingCity", "OwnerCity"])
    state = _get_first_by_keys(raw_lead, ["State", "MailingState"])
    email = _get_first_by_keys(raw_lead, ["Email", "OwnerEmail"])
    address = _get_first_by_keys(raw_lead, ["Address", "MailingAddress", "PropertyAddress"])
    score_raw = _get_first_by_keys(raw_lead, ["Score"])
    status = _get_first_by_keys(raw_lead, ["Status"]) or "New"

    score: Optional[float] = None
    if score_raw is not None:
        try:
            score = float(score_raw)
        except ValueError:
            score = None

    return {
        "name": name,
        "phone": phone,
        "city": city,
        "state": state,
        "email": email,
        "address": address,
        "score": score,
        "source": source,
        "status": status,
    }


def rei_score_lead(normalized_lead: Dict[str, Any]) -> Dict[str, Any]:
    if normalized_lead.get("score") is not None:
        return normalized_lead

    score = 50.0
    # Simple heuristic: reward having both phone and city
    if normalized_lead.get("phone"):
        score += 20.0
    if normalized_lead.get("city"):
        score += 10.0
    if normalized_lead.get("address"):
        score += 10.0

    normalized_lead["score"] = score
    return normalized_lead


def rei_prepare_lead_record(scored_lead: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "Name": scored_lead.get("name"),
        "Phone": scored_lead.get("phone"),
        "City": scored_lead.get("city"),
        "State": scored_lead.get("state"),
        "Email": scored_lead.get("email"),
        "Address": scored_lead.get("address"),
        "Score": scored_lead.get("score"),
        "Source": scored_lead.get("source"),
        "Status": scored_lead.get("status") or "New",
    }
    return {"fields": _clean_fields(fields)}


def rei_ingest_leads(source_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = source_config or _rei_feed_config_from_env()
    source_name = config.get("source_name") or "FREE_REI_FEED_URL"

    raw_leads = rei_free_feed_fetch_raw_leads(config)
    prepared_records: List[Dict[str, Any]] = []
    for raw in raw_leads:
        normalized = rei_normalize_lead(raw, source=source_name)
        if not normalized.get("phone"):
            # Skip leads without phone
            continue
        scored = rei_score_lead(normalized)
        record = rei_prepare_lead_record(scored)
        prepared_records.append(record)

    ingested_count = 0
    if prepared_records:
        result = airtable_upsert_records("Leads_REI", prepared_records)
        ingested_count = len(result.get("created", [])) + len(result.get("updated", []))

    summary = {
        "engine": "REI_DISPO_ENGINE",
        "source": source_name,
        "raw_count": len(raw_leads),
        "ingested": ingested_count,
    }
    kpi_log("REI_DISPO_ENGINE", "leads_ingested", ingested_count, extra_context=summary)
    log_ops(f"[REI_INGEST] source={source_name} raw={len(raw_leads)} ingested={ingested_count}")
    return summary


def rei_fetch_outreach_ready_leads(selection_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    max_batch_size = get_int_env("REI_SMS_MAX_PER_RUN", 30)
    query_params: Dict[str, Any] = {
        "filterByFormula": "AND({Status}='New', {Phone}!='')",
        "maxRecords": max_batch_size,
    }
    if selection_config:
        query_params.update(selection_config)
    return airtable_fetch_records("Leads_REI", query_params)


def rei_build_sms_body(lead_record: Dict[str, Any]) -> str:
    fields = lead_record.get("fields", {})
    name = fields.get("Name") or "there"
    city = fields.get("City") or "your area"
    msg = (
        f"Hi {name}, I’m looking to buy a property in {city}. "
        f"Would you consider a cash offer for your place? If yes, reply YES."
    )
    return msg


def rei_send_sms_for_lead(lead_record: Dict[str, Any], sms_body: str) -> Dict[str, Any]:
    fields = lead_record.get("fields", {})
    phone = fields.get("Phone")
    result: Dict[str, Any] = {"success": False, "error": None, "twilio": None}
    try:
        tw = twilio_send_sms(phone, sms_body)
        result["success"] = True
        result["twilio"] = tw
    except Exception as exc:
        result["error"] = str(exc)
        cracks_tracker_log_record(
            context_type="REI_SMS",
            context_payload={"lead_id": lead_record.get("id"), "fields": fields},
            error_description=str(exc),
        )
        log_error("rei_send_sms_for_lead failed", exc)
    return result


def rei_update_lead_after_sms(lead_record: Dict[str, Any], sms_result: Dict[str, Any]) -> None:
    if not sms_result.get("success"):
        return
    record_id = lead_record.get("id")
    if not record_id:
        return
    fields = {
        "Status": "Contacted",
        "Last_SMS": _now_iso(),
    }
    try:
        airtable_upsert_records("Leads_REI", [{"id": record_id, "fields": fields}])
    except Exception as exc:
        cracks_tracker_log_record(
            context_type="REI_SMS_UPDATE",
            context_payload={"lead_id": record_id},
            error_description=str(exc),
        )
        log_error("rei_update_lead_after_sms failed", exc)


def rei_sms_blast(max_batch_size: Optional[int] = None, selection_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if max_batch_size is None:
        max_batch_size = get_int_env("REI_SMS_MAX_PER_RUN", 30)

    leads = rei_fetch_outreach_ready_leads(selection_config=selection_config)
    leads = leads[:max_batch_size]

    sent = 0
    failed = 0
    for lead in leads:
        body = rei_build_sms_body(lead)
        result = rei_send_sms_for_lead(lead, body)
        if result.get("success"):
            sent += 1
            rei_update_lead_after_sms(lead, result)
        else:
            failed += 1

    summary = {
        "engine": "REI_DISPO_ENGINE",
        "attempted": len(leads),
        "sent": sent,
        "failed": failed,
    }
    kpi_log("REI_DISPO_ENGINE", "sms_sent", sent, extra_context=summary)
    log_ops(f"[REI_SMS] attempted={len(leads)} sent={sent} failed={failed}")
    return summary


def run_rei_loop(cli_args: Optional[List[str]] = None) -> Dict[str, Any]:
    ingest_mode = get_env("REI_INGEST_MODE", "disabled").lower()
    overall_summary: Dict[str, Any] = {"engine": "REI_DISPO_ENGINE"}

    try:
        if ingest_mode != "disabled":
            ingest_summary = rei_ingest_leads()
            overall_summary["ingest"] = ingest_summary
    except Exception as exc:
        overall_summary["ingest_error"] = str(exc)
        log_error("run_rei_loop ingest failed", exc)

    try:
        sms_summary = rei_sms_blast()
        overall_summary["sms"] = sms_summary
    except Exception as exc:
        overall_summary["sms_error"] = str(exc)
        log_error("run_rei_loop sms failed", exc)

    return overall_summary


# ---------------------------------------------------------------------------
# GOVCON_SUBTRAP_ENGINE – SAM.gov ingestion + Discord digest
# ---------------------------------------------------------------------------


def _parse_naics_whitelist(env_value: Optional[str]) -> List[str]:
    if not env_value:
        return []
    parts = [p.strip() for p in env_value.split(",")]
    return [p for p in parts if p]


def govcon_sam_fetch_raw_opportunities(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Fetch raw opportunities from SAM.gov Get Opportunities v2 API.

    Requirements:
    - GOVCON_SAM_API_KEY env var must contain a valid SAM.gov public API key.
    - NAICS filter must be provided via:
        - config["naics_list"] (list of strings), OR
        - GOVCON_NAICS_WHITELIST env var (comma-separated NAICS codes).
    - Date filters:
        - postedFrom/postedTo are required by the API and are set to a recent window.
        - Response deadline window is also constrained using rdlfrom/rdlto.

    If the required inputs are not configured, this function raises a RuntimeError
    with a clear MISSING_INPUT explanation.
    """
    api_key = require_env_var("GOVCON_SAM_API_KEY")
    naics_list = config.get("naics_list") or _parse_naics_whitelist(get_env("GOVCON_NAICS_WHITELIST"))
    if not naics_list:
        raise RuntimeError(
            "MISSING_INPUT: configure GOVCON_NAICS_WHITELIST or source_config['naics_list'] "
            "with at least one NAICS code."
        )

    today = datetime.date.today()
    posted_days_back = get_int_env("GOVCON_POSTED_DAYS_BACK", 7)
    rdl_days_ahead = get_int_env("GOVCON_RDL_DAYS_AHEAD", 30)

    posted_from = today - datetime.timedelta(days=posted_days_back)
    posted_to = today
    rdl_from = today
    rdl_to = today + datetime.timedelta(days=rdl_days_ahead)

    def fmt(d: datetime.date) -> str:
        return d.strftime("%m/%d/%Y")

    base_url = "https://api.sam.gov/opportunities/v2/search"
    max_records_total = config.get("max_records_total") or get_int_env("GOVCON_MAX_RECORDS_TOTAL", 100)
    limit_per_request = config.get("limit_per_request") or 50
    if limit_per_request > 1000:
        limit_per_request = 1000

    results: List[Dict[str, Any]] = []

    for naics in naics_list:
        offset = 0
        while len(results) < max_records_total:
            params = {
                "api_key": api_key,
                "postedFrom": fmt(posted_from),
                "postedTo": fmt(posted_to),
                "rdlfrom": fmt(rdl_from),
                "rdlto": fmt(rdl_to),
                "ncode": naics,
                "limit": limit_per_request,
                "offset": offset,
            }
            url = f"{base_url}?{urllib.parse.urlencode(params)}"
            status, resp_headers, resp_body = http_request_raw("GET", url)
            text = resp_body.decode("utf-8", errors="replace") if resp_body else ""
            if status == 404:
                # No data for this query; stop this NAICS
                break
            if status < 200 or status >= 300:
                raise RuntimeError(f"SAM.gov HTTP {status} for ncode={naics}: {text[:500]}")
            try:
                data = json.loads(text) if text else {}
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"SAM.gov JSON parse error for ncode={naics}: {exc}") from exc

            opps = data.get("opportunitiesData") or []
            if not isinstance(opps, list) or not opps:
                break
            for opp in opps:
                if not isinstance(opp, dict):
                    continue
                results.append(opp)
                if len(results) >= max_records_total:
                    break

            total = data.get("totalRecords")
            limit_val = data.get("limit", limit_per_request)
            if total is None or limit_val is None:
                break
            try:
                total_int = int(total)
                limit_int = int(limit_val)
            except (TypeError, ValueError):
                break

            offset += limit_int
            if offset >= total_int:
                break

        if len(results) >= max_records_total:
            break

    return results


def govcon_normalize_opportunity(raw_opp: Dict[str, Any], source: str) -> Dict[str, Any]:
    title = raw_opp.get("title")
    agency = raw_opp.get("fullParentPathName") or raw_opp.get("department")
    solicitation = raw_opp.get("solicitationNumber")
    response_deadline = raw_opp.get("responseDeadLine") or raw_opp.get("reponseDeadLine")
    naics = raw_opp.get("naicsCode")
    est_value = None

    award = raw_opp.get("award") or raw_opp.get("data", {}).get("award") if isinstance(raw_opp.get("data"), dict) else None
    if isinstance(award, dict):
        amount = award.get("amount")
        if amount is not None:
            try:
                est_value = float(str(amount).replace(",", ""))
            except ValueError:
                est_value = None

    # Use uiLink or description (which is itself a URL)
    url = raw_opp.get("uiLink") or raw_opp.get("description")

    # Normalize response deadline into ISO date if possible
    response_date_iso = None
    if isinstance(response_deadline, str) and response_deadline.strip():
        # SAM can return YYYY-MM-DD or MM/DD/YYYY, so handle both.
        s = response_deadline.strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S"):
            try:
                d = datetime.datetime.strptime(s, fmt).date()
                response_date_iso = d.isoformat()
                break
            except ValueError:
                continue

    return {
        "title": title,
        "agency": agency,
        "solicitation": solicitation,
        "response_date": response_date_iso,
        "url": url,
        "naics": naics,
        "estimated_value": est_value,
        "source": source,
    }


def govcon_score_opportunity(normalized_opp: Dict[str, Any]) -> Dict[str, Any]:
    score = 50.0
    today = datetime.date.today()
    response_date_iso = normalized_opp.get("response_date")

    if response_date_iso:
        try:
            due_date = datetime.date.fromisoformat(response_date_iso)
            days_until_due = (due_date - today).days
            if 0 <= days_until_due <= 7:
                score += 30.0
            elif 0 <= days_until_due <= 30:
                score += 15.0
        except ValueError:
            pass

    if normalized_opp.get("naics"):
        score += 10.0

    est_value = normalized_opp.get("estimated_value")
    if isinstance(est_value, (int, float)):
        if est_value >= 1_000_000:
            score += 10.0
        elif est_value >= 100_000:
            score += 5.0

    normalized_opp["score"] = score
    return normalized_opp


def govcon_prepare_opportunity_record(scored_opp: Dict[str, Any]) -> Dict[str, Any]:
    fields = {
        "Title": scored_opp.get("title"),
        "Agency": scored_opp.get("agency"),
        "Solicitation": scored_opp.get("solicitation"),
        "ResponseDate": scored_opp.get("response_date"),
        "URL": scored_opp.get("url"),
        "NAICS": scored_opp.get("naics"),
        "EstimatedValue": scored_opp.get("estimated_value"),
        "Score": scored_opp.get("score"),
        "Source": scored_opp.get("source"),
        "Status": "New",
    }
    return {"fields": _clean_fields(fields)}


def govcon_ingest_opportunities(source_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ingest_mode = get_env("GOVCON_INGEST_MODE", "disabled").lower()
    if ingest_mode == "disabled":
        return {
            "engine": "GOVCON_SUBTRAP_ENGINE",
            "ingested": 0,
            "note": "GOVCON_INGEST_MODE=disabled",
        }

    if ingest_mode != "sam_api":
        raise RuntimeError(
            "MISSING_INPUT: GOVCON_INGEST_MODE must be 'disabled' or 'sam_api'. "
            "Configure SAM.gov API access before enabling."
        )

    config = source_config or {}
    raw_opps = govcon_sam_fetch_raw_opportunities(config)

    prepared_records: List[Dict[str, Any]] = []
    for raw in raw_opps:
        normalized = govcon_normalize_opportunity(raw, source="SAM.gov")
        scored = govcon_score_opportunity(normalized)
        record = govcon_prepare_opportunity_record(scored)
        prepared_records.append(record)

    ingested_count = 0
    if prepared_records:
        result = airtable_upsert_records("GovCon_Opportunities", prepared_records)
        ingested_count = len(result.get("created", [])) + len(result.get("updated", []))

    summary = {
        "engine": "GOVCON_SUBTRAP_ENGINE",
        "raw_count": len(raw_opps),
        "ingested": ingested_count,
    }
    kpi_log("GOVCON_SUBTRAP_ENGINE", "opps_ingested", ingested_count, extra_context=summary)
    log_ops(f"[GOVCON_INGEST] raw={len(raw_opps)} ingested={ingested_count}")
    return summary


def govcon_fetch_digest_candidates(selection_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    max_opps = get_int_env("GOVCON_MAX_OPPS_PER_DIGEST", 20)
    query_params: Dict[str, Any] = {
        "filterByFormula": 'OR({Status}="New", {Status}="Open")',
        "maxRecords": max_opps,
        "sort[0][field]": "Score",
        "sort[0][direction]": "desc",
        "sort[1][field]": "ResponseDate",
        "sort[1][direction]": "asc",
    }
    if selection_config:
        query_params.update(selection_config)
    return airtable_fetch_records("GovCon_Opportunities", query_params)


def govcon_rank_opportunities(opp_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Records are already sorted via Airtable API; return as-is.
    return list(opp_records)


def govcon_build_discord_digest(ranked_opps: List[Dict[str, Any]]) -> str:
    if not ranked_opps:
        return "No GovCon opportunities to notify."

    lines = ["GovCon Opportunities Digest:"]
    for opp in ranked_opps:
        fields = opp.get("fields", {})
        title = fields.get("Title") or "Untitled"
        agency = fields.get("Agency") or "Unknown agency"
        sol = fields.get("Solicitation") or "N/A"
        resp = fields.get("ResponseDate") or "N/A"
        score = fields.get("Score") or "N/A"
        url = fields.get("URL") or "N/A"
        line = f"- {title} | {agency} | SOL: {sol} | Due: {resp} | Score: {score} | {url}"
        lines.append(line)

    digest = "\n".join(lines)
    return digest


def govcon_post_digest_to_discord(digest_text: str) -> None:
    log_ops(digest_text)


def govcon_mark_opportunities_notified(opp_records: List[Dict[str, Any]]) -> None:
    if not opp_records:
        return
    now = _now_iso()
    updates = []
    for opp in opp_records:
        rid = opp.get("id")
        if not rid:
            continue
        fields = {
            "Status": "Notified",
            "Last_Notify": now,
        }
        updates.append({"id": rid, "fields": fields})
    if updates:
        airtable_upsert_records("GovCon_Opportunities", updates)


def govcon_digest_loop(selection_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    opps = govcon_fetch_digest_candidates(selection_config=selection_config)
    ranked = govcon_rank_opportunities(opps)
    if not ranked:
        summary = {
            "engine": "GOVCON_SUBTRAP_ENGINE",
            "notified": 0,
            "note": "No digest candidates.",
        }
        kpi_log("GOVCON_SUBTRAP_ENGINE", "opps_notified", 0, extra_context=summary)
        log_ops("[GOVCON_DIGEST] No opportunities to notify.")
        return summary

    digest = govcon_build_discord_digest(ranked)
    govcon_post_digest_to_discord(digest)
    govcon_mark_opportunities_notified(ranked)

    notified_count = len(ranked)
    summary = {
        "engine": "GOVCON_SUBTRAP_ENGINE",
        "notified": notified_count,
    }
    kpi_log("GOVCON_SUBTRAP_ENGINE", "opps_notified", notified_count, extra_context=summary)
    log_ops(f"[GOVCON_DIGEST] notified={notified_count}")
    return summary


def run_govcon_loop(cli_args: Optional[List[str]] = None) -> Dict[str, Any]:
    overall_summary: Dict[str, Any] = {"engine": "GOVCON_SUBTRAP_ENGINE"}

    try:
        ingest_summary = govcon_ingest_opportunities()
        overall_summary["ingest"] = ingest_summary
    except Exception as exc:
        overall_summary["ingest_error"] = str(exc)
        log_error("run_govcon_loop ingest failed", exc)

    try:
        digest_summary = govcon_digest_loop()
        overall_summary["digest"] = digest_summary
    except Exception as exc:
        overall_summary["digest_error"] = str(exc)
        log_error("run_govcon_loop digest failed", exc)

    return overall_summary


# ---------------------------------------------------------------------------
# HEALTH ENTRYPOINT
# ---------------------------------------------------------------------------


def run_health_check(cli_args: Optional[List[str]] = None) -> Dict[str, Any]:
    summary = health_check_all()
    return summary


# ---------------------------------------------------------------------------
# CLI ENTRYPOINT
# ---------------------------------------------------------------------------


def main(argv: List[str]) -> None:
    if len(argv) < 2:
        sys.stderr.write("Usage: python krizzy_bots.py [rei|govcon|health]\n")
        sys.exit(1)

    command = argv[1].lower()
    try:
        if command == "rei":
            summary = run_rei_loop(argv[2:])
        elif command == "govcon":
            summary = run_govcon_loop(argv[2:])
        elif command == "health":
            summary = run_health_check(argv[2:])
        else:
            sys.stderr.write("Usage: python krizzy_bots.py [rei|govcon|health]\n")
            sys.exit(1)
    except Exception as exc:
        log_error(f"Unhandled exception in command '{command}'", exc)
        raise

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv)
