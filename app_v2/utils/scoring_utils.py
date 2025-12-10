from typing import Optional, Tuple
from app_v2 import config


def compute_mao(arv: float, repairs: float) -> float:
    """
    Compute Maximum Allowable Offer (MAO)
    MAO = ARV * 0.70 - Repairs
    """
    return (arv * config.MAO_MULTIPLIER) - repairs


def compute_spread(arv: float, asking: float, repairs: float) -> float:
    """
    Compute deal spread
    Spread = ARV - Asking - Repairs
    """
    return arv - asking - repairs


def compute_spread_ratio(arv: float, spread: float) -> float:
    """
    Compute spread as ratio of ARV
    Spread Ratio = Spread / ARV
    """
    if arv <= 0:
        return 0.0
    return spread / arv


def score_equity(arv: float, asking: float, repairs: float) -> Tuple[float, str, str]:
    """
    Score deal equity potential
    Returns: (equity_score, strategy, risk_flags)
    """
    if arv <= 0:
        return 0.0, "TRASH", "INVALID_ARV"

    spread = compute_spread(arv, asking, repairs)
    spread_ratio = compute_spread_ratio(arv, spread)
    mao = compute_mao(arv, repairs)

    # Risk flags
    flags = []
    if arv < 50000:
        flags.append("LOW_ARV")
    if asking > arv:
        flags.append("ASKING_EXCEEDS_ARV")
    if repairs > arv * 0.5:
        flags.append("HIGH_REPAIR_RATIO")
    if spread < 0:
        flags.append("NEGATIVE_SPREAD")

    risk_flags = ",".join(flags) if flags else None

    # Strategy determination
    if spread_ratio >= 0.25:
        strategy = "FLIP"
    elif spread_ratio >= 0.15:
        strategy = "WHOLESALE"
    elif spread_ratio >= 0.05:
        strategy = "RENTAL"
    else:
        strategy = "TRASH"

    # Equity score (0-100)
    equity_score = min(100.0, spread_ratio * 200)

    return equity_score, strategy, risk_flags


def compute_buyer_match_score(
    deal_zip: str,
    deal_price: float,
    deal_repairs: float,
    buyer_zips: list,
    buyer_min_price: Optional[float],
    buyer_max_price: Optional[float],
    buyer_rehab_appetite: Optional[str],
    buyer_response_rate: float
) -> float:
    """
    Compute buyer-deal match score (0-100)
    Uses weighted criteria from config
    """
    score = 0.0

    # ZIP match
    zip_match = 1.0 if deal_zip in (buyer_zips or []) else 0.0
    score += zip_match * config.BUYER_MATCH_WEIGHTS["zip_match"] * 100

    # Price range match
    price_match = 0.0
    if buyer_min_price is not None and buyer_max_price is not None:
        if buyer_min_price <= deal_price <= buyer_max_price:
            price_match = 1.0
        elif deal_price < buyer_min_price:
            # Close but below
            ratio = deal_price / buyer_min_price
            price_match = max(0.0, ratio - 0.5) * 2  # 50-100% = 0-1 score
        else:
            # Close but above
            ratio = buyer_max_price / deal_price
            price_match = max(0.0, ratio - 0.5) * 2
    score += price_match * config.BUYER_MATCH_WEIGHTS["price_range"] * 100

    # Rehab appetite
    rehab_match = 0.5  # Default neutral
    if buyer_rehab_appetite:
        if deal_repairs < 10000:
            rehab_match = 1.0 if buyer_rehab_appetite == "LIGHT" else 0.7
        elif deal_repairs < 50000:
            rehab_match = 1.0 if buyer_rehab_appetite == "MODERATE" else 0.8
        else:
            rehab_match = 1.0 if buyer_rehab_appetite == "HEAVY" else 0.6
    score += rehab_match * config.BUYER_MATCH_WEIGHTS["rehab_appetite"] * 100

    # Past responsiveness
    score += buyer_response_rate * config.BUYER_MATCH_WEIGHTS["past_responsiveness"] * 100

    return min(100.0, score)
