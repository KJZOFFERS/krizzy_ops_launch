# src/engines/govcon_engine.py
import asyncio
from src.engines.scorer import Scorer

class GovConEngine:

    def __init__(self, airtable, discord, kpi):
        self.at = airtable
        self.ds = discord
        self.kpi = kpi

    async def run(self):
        ops = await self.at.fetch("GovCon_Opportunities")

        processed = 0
        tasks = []

        for row in ops:
            fields = row["fields"]

            score = Scorer.score_govcon(fields)

            update_fields = {
                "Score": score,
                "Status": "SCANNED"
            }

            if score >= 65:
                update_fields["BidReady"] = True

                msg = (
                    f"📄 Bid Ready\n"
                    f"NAICS: {fields.get('NAICS')}\n"
                    f"Value: {fields.get('Value')}\n"
                    f"Score: {score}"
                )
                tasks.append(self.ds.send_ops(msg))

            tasks.append(
                self.at.update(
                    "GovCon_Opportunities",
                    row["id"],
                    update_fields
                )
            )

            processed += 1

        await asyncio.gather(*tasks)

        await self.kpi.log("GOVCON_ENGINE", {"processed": processed})
        await self.ds.send_ops(f"🏁 GovCon Engine complete | {processed} ops processed")

        return {"processed": processed}
