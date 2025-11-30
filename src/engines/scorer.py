# src/engines/scorer.py

class Scorer:

    @staticmethod
    def score_rei(lead):
        arv = lead.get("ARV") or 0
        asking = lead.get("Asking") or 0
        repairs = lead.get("Repairs") or 0
        loc_score = lead.get("LocationScore") or 0

        if not arv or not asking:
            return 0

        spread = arv - asking - repairs
        spread_score = max(0, min(100, (spread / arv) * 100))
        loc_score = max(0, min(100, loc_score))

        final = round((spread_score * 0.7) + (loc_score * 0.3), 2)
        return final

    @staticmethod
    def score_govcon(op):
        naics_match = 100 if op.get("NAICS_Match") else 0
        value = op.get("Value") or 0
        complexity = op.get("Complexity") or 1
        competition = op.get("Competition") or 1

        value_score = min(100, value / 50000 * 100)
        complexity_score = max(0, 100 - (complexity * 20))
        competition_score = max(0, 100 - (competition * 15))

        final = (
            naics_match * 0.4 +
            value_score * 0.3 +
            complexity_score * 0.2 +
            competition_score * 0.1
        )

        return round(final, 2)
