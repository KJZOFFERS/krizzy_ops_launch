from __future__ import annotations
from typing import Any, Dict, Optional
from loguru import logger
try:
    from prometheus_client import Counter  # type: ignore
except Exception:
    class Counter:  # minimal offline stub
        def __init__(self,*a,**k): pass
        def labels(self,*a,**k): return self
        def inc(self,*a,**k): pass
        def observe(self,*a,**k): pass
        def __call__(self,*a,**k): return self
KPI_LOGGED_TOTAL = Counter("kpi_logged_total", "Total KPIs logged")
from config import get_settings
from .airtable_utils import safe_airtable_write
from .discord_utils import send_discord_message
async def log_kpi(metric: str, value: float | int, extra: Optional[Dict[str, Any]] = None) -> None:
    try:
        KPI_LOGGED_TOTAL.inc()
    except Exception:
        pass
    s = get_settings()
    fields = {"Metric": metric, "Value": float(value)}
    if extra: fields["Extra"] = str(extra)
    try:
        safe_airtable_write(s.airtable_api_key, s.airtable_kpi_base, s.airtable_kpi_table, fields)
    except Exception as e:
        logger.debug(f"KPI Airtable offline: {e}")
    try:
        await send_discord_message(s.discord_webhook_url, f"KPI: {metric} = {value}\n{extra or ''}")
    except Exception as e:
        logger.debug(f"KPI Discord offline: {e}")
