import base64
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app_v2 import config
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailClient:
    """
    Minimal Gmail wrapper for thread search + body extraction.
    Expects GMAIL_TOKEN_JSON (and optionally GMAIL_CREDENTIALS_JSON) to be set.
    """

    def __init__(self, credentials_json: str | None = None, token_json: str | None = None):
        self.credentials_json = credentials_json or config.GMAIL_CREDENTIALS_JSON
        self.token_json = token_json or config.GMAIL_TOKEN_JSON
        self.service = self._build_service()

    def _build_service(self):
        """Build Gmail service if credentials are present."""
        if not self.token_json:
            logger.warning("Gmail token not configured; skipping Gmail fetch.")
            return None

        try:
            token_data = json.loads(self.token_json)
            if self.credentials_json:
                creds_data = json.loads(self.credentials_json)
                token_data.setdefault("client_id", creds_data.get("client_id"))
                token_data.setdefault("client_secret", creds_data.get("client_secret"))
            creds = Credentials.from_authorized_user_info(token_data, scopes=SCOPES)

            if not creds.valid and creds.refresh_token:
                creds.refresh(Request())

            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return service
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialize Gmail client: %s: %s", type(exc).__name__, exc)
            return None

    def fetch_threads(
        self,
        keywords: List[str],
        *,
        max_threads: int = 15,
        newer_than_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Fetch recent Gmail threads that match any keyword."""
        if not self.service:
            return []

        query = f"({' OR '.join(keywords)}) newer_than:{newer_than_days}d"
        try:
            response = (
                self.service.users()
                .threads()
                .list(userId="me", q=query, maxResults=max_threads)
                .execute()
            )
            threads = response.get("threads", [])
        except HttpError as exc:
            logger.error("Gmail list threads error: %s", exc)
            return []

        results: List[Dict[str, Any]] = []
        for thread in threads:
            thread_id = thread.get("id")
            if not thread_id:
                continue
            try:
                detail = (
                    self.service.users()
                    .threads()
                    .get(userId="me", id=thread_id, format="full")
                    .execute()
                )
                results.append(detail)
            except HttpError as exc:
                logger.error("Gmail get thread %s error: %s", thread_id, exc)
                continue

        return results

    @staticmethod
    def _decode_part_body(part: Dict[str, Any]) -> str:
        """Decode a single MIME part body into text."""
        data = part.get("body", {}).get("data")
        if not data:
            return ""
        try:
            decoded = base64.urlsafe_b64decode(data)
            return decoded.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    @classmethod
    def _extract_payload_text(cls, payload: Dict[str, Any]) -> str:
        """Extract human-readable text from a Gmail payload tree."""
        if not payload:
            return ""

        mime_type = payload.get("mimeType", "")
        if "text/plain" in mime_type:
            return cls._decode_part_body(payload)

        parts = payload.get("parts") or []
        texts = []
        for part in parts:
            text = cls._extract_payload_text(part)
            if text:
                texts.append(text)

        return "\n".join(texts)

    @classmethod
    def parse_thread(cls, thread: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a Gmail thread into a dict with text and metadata.
        The raw thread is expected to come from fetch_threads.
        """
        thread_id = thread.get("id", "")
        messages = thread.get("messages", [])
        if not messages:
            return {"id": thread_id, "text": "", "subject": "", "from": ""}

        latest = messages[-1]
        headers = {h.get("name"): h.get("value") for h in latest.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "") or ""
        from_header = headers.get("From", "") or ""

        body_chunks: List[str] = []
        for msg in messages:
            payload = msg.get("payload", {})
            chunk = cls._extract_payload_text(payload)
            if chunk:
                body_chunks.append(chunk)

        text = "\n".join([subject, thread.get("snippet", "")] + body_chunks)
        internal_ts = latest.get("internalDate")
        timestamp = None
        if internal_ts:
            try:
                timestamp = datetime.fromtimestamp(int(internal_ts) / 1000, tz=timezone.utc)
            except Exception:
                timestamp = None

        return {
            "id": thread_id,
            "subject": subject,
            "from": from_header,
            "text": text,
            "timestamp": timestamp,
        }


def extract_address(text: str) -> Optional[str]:
    """Heuristic address extraction from email text."""
    patterns = [
        r"\d{3,6}\s+[A-Za-z0-9\.\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\.?,?\s+[A-Za-z\.\s]+,\s*[A-Z]{2}\s*\d{5}",
        r"\d{3,6}\s+[A-Za-z0-9\.\s]+,\s*[A-Za-z\.\s]+,\s*[A-Z]{2}\s*\d{5}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def extract_price(text: str) -> Optional[float]:
    """Find an asking/offer price in the text."""
    price_match = re.search(
        r"(?:asking|offer|price|contract)\s*(?:at|is|:)?\s*\$?([\d,]{2,})",
        text,
        flags=re.IGNORECASE,
    )
    if not price_match:
        return None
    raw = price_match.group(1).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return None


def extract_deadline(text: str) -> Optional[datetime]:
    """Search for a deadline style date (MM/DD or YYYY-MM-DD)."""
    date_patterns = [
        r"(?:deadline|by|due)\s*(?:on|by)?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"(?:deadline|by|due)\s*(?:on|by)?\s*(\d{4}-\d{1,2}-\d{1,2})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw_date = match.group(1)
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw_date, fmt)
                return parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def extract_sender_name(from_header: str) -> Optional[str]:
    """Extract sender display name from From header."""
    if not from_header:
        return None
    match = re.match(r'"?([^"<]+)"?\s*(?:<.*>)?', from_header)
    if match:
        return match.group(1).strip()
    return from_header.strip() or None
