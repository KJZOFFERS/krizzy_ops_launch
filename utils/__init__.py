import math

def zip_distance(zip1: str, zip2: str) -> int:
    """Simple numeric zip distance. Lower = closer."""
    try:
        return abs(int(zip1) - int(zip2))
    except:
        return 99999

def match_buyers_to_lead(lead_zip: str, lead_price: float, buyers: list):
    """
    Returns list of buyers who match:
    - Similar zip proximity
    - budget_max >= ask price
    - opted_out != True
    """
    matches = []
    for b in buyers:
        f = b.get("fields", {})
        if f.get("opted_out"):
            continue

        buyer_zip = f.get("zip")
        budget = f.get("budget_max")

        if not buyer_zip or not budget:
            continue
        if float(budget) < float(lead_price):
            continue

        dist = zip_distance(str(lead_zip), str(buyer_zip))
        matches.append((dist, b))

    matches.sort(key=lambda x: x[0])
    return [m[1] for m in matches]
