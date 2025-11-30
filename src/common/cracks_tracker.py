# src/common/cracks_tracker.py
import datetime

class CracksTracker:
    def __init__(self, airtable, discord):
        self.at = airtable
        self.ds = discord

    async def log(self, description, details=None):
        record = {
            "Description": description,
            "Details": str(details) if details else "",
            "Timestamp": datetime.datetime.utcnow().isoformat()
        }
        await self.at.create("Cracks_Tracker", record)
        await self.ds.send_error(description)
