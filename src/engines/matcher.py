# src/engines/matcher.py

class Matcher:
    @staticmethod
    def match_buyer(lead, buyers):
        arv = lead.get("ARV") or 0
        zipc = str(lead.get("Zip") or "")

        matches = []
        for b in buyers:
            max_price = b.get("MaxPrice") or 0
            zones = b.get("Zones") or []
            liquidity = b.get("Liquidity") or 0

            if arv <= max_price and zipc in zones and liquidity >= arv * 0.2:
                matches.append(b)

        return matches
