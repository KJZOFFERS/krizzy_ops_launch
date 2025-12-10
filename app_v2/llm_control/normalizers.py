import re
from typing import Any, Dict, Optional


def normalize_rei(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw REI text/payload into structured dict for Leads_REI.

    Expected input:
      { "text": "<raw text from SMS/scrape/form>", ... }

    Returns structured dict with:
      - address, city, state, zip
      - asking, arv, repairs (floats)
      - notes (original text)
    """
    text = str(raw.get("text", "")).strip()

    return {
        "address": _extract(text, r"\d{1,6}\s[\w\s\.]+"),
        "asking": _extract_money(text, r"(?i)asking[:\s]*\$?([\d,]+)"),
        "arv": _extract_money(text, r"(?i)arv[:\s]*\$?([\d,]+)"),
        "repairs": _extract_money(text, r"(?i)repairs?[:\s]*\$?([\d,]+)"),
        "city": _extract(text, r"(?i)(?:city|in)[:\s]*([\w\s]+)"),
        "state": _extract(text, r"\b([A-Z]{2})\b"),
        "zip": _extract(text, r"\b(\d{5}(?:-\d{4})?)\b"),
        "notes": text,
    }


def normalize_govcon(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw GovCon text into structured dict for GovCon_Opportunities.

    Expected input:
      { "text": "<synopsis/solicitation text>", ... }

    Returns structured dict with:
      - naics, set_aside, due_date, title, agency
      - description (original text)
    """
    text = str(raw.get("text", "")).strip()

    return {
        "naics": _extract(text, r"\b(\d{6})\b"),
        "due_date": _extract(text, r"(?i)(?:due|deadline|response)[:\s]*([A-Za-z0-9,\s/-]+?)(?:\.|$)"),
        "set_aside": _extract(text, r"(?i)set[- ]aside[:\s]*([\w\s/]+?)(?:\.|$)"),
        "title": _extract(text, r"(?i)(?:title|solicitation)[:\s]*([\w\s]+?)(?:\.|$)"),
        "agency": _extract(text, r"(?i)agency[:\s]*([\w\s]+?)(?:\.|$)"),
        "description": text,
    }


def normalize_buyer(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw buyer text into structured dict for REI_Buyers.

    Expected input:
      { "text": "<buyer profile text>", ... }

    Returns structured dict with:
      - name, phone, email
      - market_city, market_state
      - min_price, max_price
      - rehab_appetite, strategy
    """
    text = str(raw.get("text", "")).strip()

    return {
        "name": _extract(text, r"(?i)(?:name|buyer)[:\s]*([\w\s]+?)(?:\.|$)"),
        "phone": _extract(text, r"(?:\+1[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}"),
        "email": _extract(text, r"[\w\.-]+@[\w\.-]+\.\w+"),
        "market_city": _extract(text, r"(?i)(?:market|city|looking in)[:\s]*([\w\s]+?)(?:\.|,|$)"),
        "market_state": _extract(text, r"\b([A-Z]{2})\b"),
        "min_price": _extract_money(text, r"(?i)(?:min|minimum|from)[:\s]*\$?([\d,]+)"),
        "max_price": _extract_money(text, r"(?i)(?:max|maximum|to|up to)[:\s]*\$?([\d,]+)"),
        "rehab_appetite": _extract(text, r"(?i)(?:rehab|renovation)[:\s]*(light|moderate|heavy)"),
        "strategy": _extract(text, r"(?i)(?:strategy|looking for)[:\s]*(flip|rental|wholesale|buy and hold)"),
    }


def _extract(text: str, pattern: str) -> Optional[str]:
    """Extract first match from text using regex pattern"""
    m = re.search(pattern, text)
    if not m:
        return None
    result = m.group(1) if m.groups() else m.group(0)
    return result.strip() if result else None


def _extract_money(text: str, pattern: str) -> Optional[float]:
    """Extract monetary value from text and convert to float"""
    m = re.search(pattern, text)
    if not m:
        return None
    raw = m.group(1) if m.groups() else m.group(0)
    try:
        return float(str(raw).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None
