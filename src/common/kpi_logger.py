# src/common/kpi_logger.py
import datetime

class KPILogger:
    def __init__(self, airtable):
        self.at = airtable

    async def log(self, engine, stats: dict):
        entry = {
            "Engine": engine,
            "Timestamp": datetime.datetime.utcnow().isoformat(),
            "Stats": str(stats)
        }
        await self.at.create("KPI_Log", entry)
