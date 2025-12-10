from typing import Any, Dict


def score_rei(deal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute MAO, spread, and score for an REI deal.

    Input keys: asking, arv, repairs (floats or convertible)

    Returns:
      - mao: Maximum Allowable Offer (ARV * 0.70 - repairs)
      - spread: Profit potential (ARV - asking - repairs)
      - score: 0-100 numeric score
      - recommendation: "assign", "wholesale", "rental", or "trash"
    """
    asking = _to_float(deal.get("asking") or deal.get("Asking"))
    arv = _to_float(deal.get("arv") or deal.get("ARV"))
    repairs = _to_float(deal.get("repairs") or deal.get("Repairs"))

    mao = 0.70 * arv - repairs
    spread = arv - asking - repairs
    spread_ratio = spread / arv if arv > 0 else 0.0

    # Determine recommendation
    if spread >= 50000:
        recommendation = "assign"
    elif spread >= 30000:
        recommendation = "wholesale"
    elif spread >= 10000:
        recommendation = "rental"
    else:
        recommendation = "trash"

    return {
        "mao": round(mao, 2),
        "spread": round(spread, 2),
        "spread_ratio": round(spread_ratio, 4),
        "score": _score_spread(spread),
        "recommendation": recommendation,
    }


def score_govcon(op: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score GovCon opportunity based on NAICS, set-aside, and keywords.

    Returns:
      - score: 0-100 numeric score
      - recommendation: "bid" or "skip"
    """
    score = 0

    # Extract fields (handle case variations)
    naics = str(op.get("naics") or op.get("NAICS") or "")
    set_aside = str(op.get("set_aside") or op.get("Set_Aside") or "").lower()
    desc = str(op.get("description") or op.get("Description") or "").lower()
    title = str(op.get("title") or op.get("Title") or "").lower()

    # NAICS scoring (IT/construction/services)
    high_value_naics = {"236220", "238160", "561720", "541330", "541511", "541512", "541519"}
    if naics in high_value_naics:
        score += 30

    # Set-aside scoring
    favorable_set_asides = ["small business", "8(a)", "sdvosb", "wosb", "hubzone"]
    if any(term in set_aside for term in favorable_set_asides):
        score += 25

    # Keyword scoring in description/title
    favorable_keywords = [
        "maintenance", "repair", "construction", "consulting", "it services",
        "software", "cybersecurity", "cloud", "infrastructure"
    ]
    keyword_count = sum(1 for kw in favorable_keywords if kw in desc or kw in title)
    score += min(20, keyword_count * 5)

    # Estimated value scoring (if available)
    estimated_value = _to_float(op.get("estimated_value") or op.get("Estimated_Value"))
    if estimated_value >= 100000:
        score += 15
    elif estimated_value >= 50000:
        score += 10

    # Cap at 100
    score = min(100, score)

    recommendation = "bid" if score >= 50 else "skip"

    return {
        "score": score,
        "recommendation": recommendation,
    }


def score_buyer(buyer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score buyer based on liquidity indicators and intent signals.

    Returns:
      - liquidity_score: 0-100 (higher = more liquid)
      - intent: "high", "medium", "low", or "unknown"
      - tier_recommendation: "A", "B", or "C"
    """
    # Flatten all values to searchable text
    tags = " ".join(str(v).lower() for v in buyer.values() if v)

    liquidity_score = 40  # Base score

    # Liquidity signals
    if "cash" in tags or "wire" in tags or "proof of funds" in tags:
        liquidity_score += 30
    if "closes fast" in tags or "7 days" in tags or "quick close" in tags:
        liquidity_score += 20
    if "hard money" in tags or "private lender" in tags:
        liquidity_score += 10

    # Cap at 100
    liquidity_score = min(100, liquidity_score)

    # Intent signals
    intent = "unknown"
    if any(phrase in tags for phrase in ["actively buying", "buying now", "ready to close"]):
        intent = "high"
    elif any(phrase in tags for phrase in ["looking", "interested", "considering"]):
        intent = "medium"
    elif any(phrase in tags for phrase in ["maybe", "just browsing", "not sure"]):
        intent = "low"

    # Tier recommendation
    if liquidity_score >= 80 and intent == "high":
        tier = "A"
    elif liquidity_score >= 60 or intent in ["high", "medium"]:
        tier = "B"
    else:
        tier = "C"

    return {
        "liquidity_score": liquidity_score,
        "intent": intent,
        "tier_recommendation": tier,
    }


def _to_float(v: Any) -> float:
    """Convert value to float, handling common formatting"""
    if v is None:
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _score_spread(spread: float) -> int:
    """Convert spread to 0-100 score"""
    if spread >= 50000:
        return 90
    if spread >= 30000:
        return 75
    if spread >= 15000:
        return 60
    if spread >= 5000:
        return 40
    if spread >= 0:
        return 20
    return 0
