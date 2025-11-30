# src/engines/rei_engine.py
import asyncio
from src.engines.scorer import Scorer
from src.engines.matcher import Matcher

class REIEngine:

    def __init__(self, airtable, discord, twilio, kpi):
        self.at = airtable
        self.ds = discord
        self.tw = twilio
        self.kpi = kpi

    async def run(self):
        leads = await self.at.fetch("Leads_REI")
        buyers = await self.at.fetch("Buyers")

        processed = 0
        tasks = []

        for row in leads:
            fields = row["fields"]

            score = Scorer.score_rei(fields)
            matches = Matcher.match_buyer(fields, [b["fields"] for b in buyers])

            update_fields = {
                "Score": score,
                "MatchedBuyers": len(matches),
                "Status": "SCANNED"
            }
            tasks.append(self.at.update("Leads_REI", row["id"], update_fields))

            if matches:
                msg = f"🔥 Deal in {fields.get('Zip')} | {len(matches)} buyer matches"
                tasks.append(self.ds.send_ops(msg))

                sms_body = (
                    f"New Deal\n"
                    f"ARV: {fields.get('ARV')}\n"
                    f"Asking: {fields.get('Asking')}\n"
                    f"Repairs: {fields.get('Repairs')}\n"
                    f"Zip: {fields.get('Zip')}"
                )

                for b in matches:
                    phone = b.get("Phone")
                    if phone:
                        tasks.append(self.tw.send_sms(phone, sms_body))

            processed += 1

        await asyncio.gather(*tasks)

        await self.kpi.log("REI_ENGINE", {"processed": processed})
        await self.ds.send_ops(f"🏁 REI Engine complete | {processed} leads processed")

        return {"processed": processed}
