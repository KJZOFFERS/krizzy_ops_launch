import os
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("krizzy_ops")


class Config:
    # Airtable
    AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
    AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
    AIRTABLE_LEADS_REI_TABLE = os.getenv("AIRTABLE_LEADS_REI_TABLE", "Leads_REI")
    AIRTABLE_BUYERS_TABLE = os.getenv("AIRTABLE_BUYERS_TABLE", "Buyers")
    AIRTABLE_GOVCON_TABLE = os.getenv("AIRTABLE_GOVCON_TABLE", "GovCon_Opportunities")
    AIRTABLE_KPI_TABLE = os.getenv("AIRTABLE_KPI_TABLE", "KPI_Log")

    # REI fields / statuses
    REI_STATUS_FIELD = os.getenv("REI_STATUS_FIELD", "Status")
    REI_PHONE_FIELD = os.getenv("REI_PHONE_FIELD", "Phone")
    REI_NAME_FIELD = os.getenv("REI_NAME_FIELD", "Name")
    REI_LAST_TOUCHED_FIELD = os.getenv("REI_LAST_TOUCHED_FIELD", "Last_Touched_At")
    REI_LAST_RESULT_FIELD = os.getenv("REI_LAST_RESULT_FIELD", "Last_Result")
    REI_STATUS_NEW_VALUE = os.getenv("REI_STATUS_NEW_VALUE", "NEW")
    REI_STATUS_TOUCHED_VALUE = os.getenv("REI_STATUS_TOUCHED_VALUE", "TOUCHED")
    REI_SMS_TEMPLATE = os.getenv(
        "REI_SMS_TEMPLATE",
        "Hey{space}{name}, this is Krizzy. I had a quick question about a property you might own. Is this the right number?",
    )

    # GovCon fields / statuses
    GOVCON_STATUS_FIELD = os.getenv("GOVCON_STATUS_FIELD", "Status")
    GOVCON_STATUS_NEW_VALUE = os.getenv("GOVCON_STATUS_NEW_VALUE", "NEW")
    GOVCON_STATUS_DIGESTED_VALUE = os.getenv("GOVCON_STATUS_DIGESTED_VALUE", "DIGESTED")
    GOVCON_DUE_DATE_FIELD = os.getenv("GOVCON_DUE_DATE_FIELD", "Due_Date")
    GOVCON_TITLE_FIELD = os.getenv("GOVCON_TITLE_FIELD", "Title")
    GOVCON_AGENCY_FIELD = os.getenv("GOVCON_AGENCY_FIELD", "Agency")
    GOVCON_SOL_FIELD = os.getenv("GOVCON_SOL_FIELD", "Sol_Number")
    GOVCON_URL_FIELD = os.getenv("GOVCON_URL_FIELD", "URL")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

    # Discord
    DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
    DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")

    # Misc
    ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")


class AirtableClient:
    """
    Simple Airtable REST client.
    Base URL: https://api.airtable.com/v0/{baseId}/{tableName}
    """

    def __init__(self, api_key: str, base_id: str) -> None:
        if not api_key or not base_id:
            raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")
        self.base_url = f"https://api.airtable.com/v0/{base_id}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def list_records(
        self,
        table: str,
        filter_formula: Optional[str] = None,
        max_records: Optional[int] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        offset: Optional[str] = None

        while True:
            params: Dict[str, Any] = {"pageSize": page_size}
            if filter_formula:
                params["filterByFormula"] = filter_formula
            if offset:
                params["offset"] = offset
            if max_records is not None:
                remaining = max_records - len(records)
                if remaining <= 0:
                    break
                params["pageSize"] = min(page_size, remaining)

            resp = self.session.get(f"{self.base_url}/{table}", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            batch = data.get("records", [])
            records.extend(batch)
            offset = data.get("offset")
            if not offset:
                break

        if max_records is not None:
            return records[:max_records]
        return records

    def update_record(self, table: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"fields": fields}
        resp = self.session.patch(
            f"{self.base_url}/{table}/{record_id}", json=payload, timeout=15
        )
        resp.raise_for_status()
        return resp.json()

    def create_record(self, table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"fields": fields}
        resp = self.session.post(f"{self.base_url}/{table}", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()


class TwilioClient:
    """
    Twilio Programmable Messaging:
    POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json
    with To, MessagingServiceSid, Body.
    """

    def __init__(self, account_sid: str, auth_token: str, messaging_service_sid: str) -> None:
        if not account_sid or not auth_token or not messaging_service_sid:
            raise ValueError("Twilio credentials and Messaging Service SID must be set")
        self.account_sid = account_sid
        self.auth = (account_sid, auth_token)
        self.messaging_service_sid = messaging_service_sid

    def send_sms(self, to: str, body: str) -> Dict[str, Any]:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": to,
            "MessagingServiceSid": self.messaging_service_sid,
            "Body": body,
        }
        resp = requests.post(url, data=data, auth=self.auth, timeout=15)
        resp.raise_for_status()
        return resp.json()


class DiscordClient:
    """
    Discord Webhook: POST JSON {"content": "..."} to webhook URL.
    """

    def __init__(self, ops_webhook: Optional[str], errors_webhook: Optional[str]) -> None:
        self.ops_webhook = ops_webhook
        self.errors_webhook = errors_webhook or ops_webhook

    def send(self, message: str, is_error: bool = False) -> None:
        url = self.errors_webhook if is_error else self.ops_webhook
        if not url:
            return
        payload = {"content": message[:2000]}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            logger.error("Failed to send message to Discord: %s", e)


def get_airtable() -> AirtableClient:
    return AirtableClient(
        api_key=Config.AIRTABLE_API_KEY,
        base_id=Config.AIRTABLE_BASE_ID,
    )


def get_twilio() -> TwilioClient:
    return TwilioClient(
        account_sid=Config.TWILIO_ACCOUNT_SID,
        auth_token=Config.TWILIO_AUTH_TOKEN,
        messaging_service_sid=Config.TWILIO_MESSAGING_SERVICE_SID,
    )


def get_discord() -> DiscordClient:
    return DiscordClient(
        ops_webhook=Config.DISCORD_WEBHOOK_OPS,
        errors_webhook=Config.DISCORD_WEBHOOK_ERRORS,
    )


def log_kpi(
    airtable: AirtableClient,
    engine: str,
    event: str,
    count: int,
    details: Optional[str] = None,
) -> None:
    try:
        airtable.create_record(
            Config.AIRTABLE_KPI_TABLE,
            {
                "Timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
                "Engine": engine,
                "Event": event,
                "Count": count,
                "Details": details or "",
                "Environment": Config.ENVIRONMENT,
            },
        )
    except Exception as e:
        logger.error("Failed to log KPI: %s", e)


def run_rei_dispo_batch(max_records: int = 50) -> Dict[str, Any]:
    """
    REI_DISPO_ENGINE:
    - Pulls NEW leads from Airtable (Leads_REI)
    - Sends SMS via Twilio
    - Updates Status + Last_Touched_At + Last_Result
    - Logs KPI + Discord
    """
    airtable = get_airtable()
    discord = get_discord()

    status_field = Config.REI_STATUS_FIELD
    phone_field = Config.REI_PHONE_FIELD
    name_field = Config.REI_NAME_FIELD
    last_touched_field = Config.REI_LAST_TOUCHED_FIELD
    last_result_field = Config.REI_LAST_RESULT_FIELD

    # AND({Status}='NEW', {Phone}!='')
    filter_formula = (
        f"AND({{{status_field}}}='{Config.REI_STATUS_NEW_VALUE}', "
        f"{{{phone_field}}}!='')"
    )

    try:
        records = airtable.list_records(
            Config.AIRTABLE_LEADS_REI_TABLE,
            filter_formula=filter_formula,
            max_records=max_records,
        )
    except Exception as e:
        discord.send(f"[REI_DISPO] Failed to pull leads: {e}", is_error=True)
        raise

    twilio = get_twilio()

    sent = 0
    errors = 0
    error_examples: List[str] = []

    from collections import defaultdict

    for record in records:
        fields = record.get("fields", {})
        phone = fields.get(phone_field)
        if not phone:
            continue

        space = " "
        name = fields.get(name_field) or ""
        template = Config.REI_SMS_TEMPLATE
        try:
            # Allow {name} and {space} tokens; ignore missing keys
            body = template.format_map(defaultdict(str, name=name, space=space))
        except Exception:
            body = template.replace("{name}", name).replace("{space}", space)

        try:
            twilio.send_sms(to=phone, body=body)
            sent += 1
            airtable.update_record(
                Config.AIRTABLE_LEADS_REI_TABLE,
                record_id=record["id"],
                fields={
                    status_field: Config.REI_STATUS_TOUCHED_VALUE,
                    last_touched_field: datetime.utcnow()
                    .replace(tzinfo=timezone.utc)
                    .isoformat(),
                    last_result_field: "SMS_SENT",
                },
            )
            # light throttle for Twilio / deliverability
            time.sleep(0.5)
        except Exception as e:
            errors += 1
            msg = f"record_id={record.get('id')} phone={phone} error={e}"
            if len(error_examples) < 5:
                error_examples.append(msg)
            logger.error("[REI_DISPO] %s", msg)

    summary = {
        "engine": "REI_DISPO_ENGINE",
        "total_pulled": len(records),
        "sent": sent,
        "errors": errors,
        "error_examples": error_examples,
    }

    discord.send(
        f"[REI_DISPO] Batch complete: pulled={len(records)} sent={sent} errors={errors}",
        is_error=errors > 0,
    )

    try:
        log_kpi(
            airtable,
            engine="REI_DISPO_ENGINE",
            event="batch_sms",
            count=sent,
            details=f"errors={errors}",
        )
    except Exception:
        pass

    return summary


def run_govcon_digest(max_records: int = 10, window_days: int = 7) -> Dict[str, Any]:
    """
    GOVCON_SUBTRAP_ENGINE:
    - Pulls NEW opps due in next N days
    - Sends Discord digest
    - Marks opps as DIGESTED
    - Logs KPI
    """
    airtable = get_airtable()
    discord = get_discord()

    status_field = Config.GOVCON_STATUS_FIELD
    due_field = Config.GOVCON_DUE_DATE_FIELD
    title_field = Config.GOVCON_TITLE_FIELD
    agency_field = Config.GOVCON_AGENCY_FIELD
    sol_field = Config.GOVCON_SOL_FIELD
    url_field = Config.GOVCON_URL_FIELD

    # AND(Status='NEW', Due_Date >= TODAY(), Due_Date <= DATEADD(TODAY(), window_days, 'days'))
    filter_formula = (
        f"AND("
        f"{{{status_field}}}='{Config.GOVCON_STATUS_NEW_VALUE}', "
        f"{{{due_field}}} >= TODAY(), "
        f"{{{due_field}}} <= DATEADD(TODAY(), {window_days}, 'days')"
        f")"
    )

    try:
        records = airtable.list_records(
            Config.AIRTABLE_GOVCON_TABLE,
            filter_formula=filter_formula,
            max_records=max_records,
        )
    except Exception as e:
        discord.send(f"[GOVCON_SUBTRAP] Failed to pull opps: {e}", is_error=True)
        raise

    lines: List[str] = []
    updated = 0

    for idx, record in enumerate(records, start=1):
        fields = record.get("fields", {})
        sol = fields.get(sol_field, "N/A")
        agency = fields.get(agency_field, "N/A")
        title = fields.get(title_field, "N/A")
        due = fields.get(due_field, "N/A")
        url = fields.get(url_field, "")

        line = f"{idx}. {sol} | {agency} | {title} | Due: {due}"
        if url:
            line += f" | {url}"
        lines.append(line)

        try:
            airtable.update_record(
                Config.AIRTABLE_GOVCON_TABLE,
                record_id=record["id"],
                fields={status_field: Config.GOVCON_STATUS_DIGESTED_VALUE},
            )
            updated += 1
        except Exception as e:
            logger.error(
                "[GOVCON_SUBTRAP] Failed to update status for %s: %s",
                record.get("id"),
                e,
            )

    if lines:
        header = f"[GOVCON_SUBTRAP] Next {len(lines)} NEW opps (<= {window_days} days):"
        body = "\n".join(lines)
        discord.send(f"{header}\n{body}")
    else:
        discord.send("[GOVCON_SUBTRAP] No NEW opps in window")

    try:
        log_kpi(
            airtable,
            engine="GOVCON_SUBTRAP_ENGINE",
            event="digest",
            count=len(records),
            details=f"updated_status={updated}",
        )
    except Exception:
        pass

    summary = {
        "engine": "GOVCON_SUBTRAP_ENGINE",
        "pulled": len(records),
        "marked_digest": updated,
    }
    return summary


app = FastAPI(title="KRIZZY OPS", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, Any]:
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    env_ok = {
        "airtable": bool(Config.AIRTABLE_API_KEY and Config.AIRTABLE_BASE_ID),
        "twilio": bool(
            Config.TWILIO_ACCOUNT_SID
            and Config.TWILIO_AUTH_TOKEN
            and Config.TWILIO_MESSAGING_SERVICE_SID
        ),
        "discord": bool(Config.DISCORD_WEBHOOK_OPS),
    }
    status = "ok" if all(env_ok.values()) else "degraded"
    return {
        "status": status,
        "service": "krizzy_ops",
        "environment": Config.ENVIRONMENT,
        "timestamp": now,
        "env": env_ok,
    }


@app.post("/run/rei_dispo")
def run_rei() -> Dict[str, Any]:
    summary = run_rei_dispo_batch()
    return summary


@app.post("/run/govcon_digest")
def run_govcon() -> Dict[str, Any]:
    summary = run_govcon_digest()
    return summary


@app.post("/run/all")
def run_all() -> Dict[str, Any]:
    rei = run_rei_dispo_batch()
    gov = run_govcon_digest()
    return {"rei": rei, "govcon": gov}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
