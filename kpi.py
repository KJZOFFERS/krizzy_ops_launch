import os
import logging
import datetime
from typing import Dict, Any, Optional
from airtable_utils import safe_airtable_write

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def kpi_push(event: str, data: Dict[str, Any]) -> None:
    """
    Push KPI event to Airtable with comprehensive error handling.
    
    Args:
        event: Event name (e.g., 'boot', 'cycle_start', 'cycle_end', 'error')
        data: Event data dictionary
    """
    try:
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.datetime.utcnow().isoformat()
        
        # Add environment info
        data['environment'] = os.getenv('ENVIRONMENT', 'production')
        data['version'] = '3.0.0'
        
        kpi_record = {
            "Event": event,
            "Data": str(data),
            "Timestamp": data['timestamp'],
            "Status": "success",
            "Environment": data['environment'],
            "Version": data['version']
        }
        
        safe_airtable_write("KPI_Log", kpi_record)
        logger.info(f"KPI pushed: {event} - {data.get('count', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Failed to push KPI {event}: {e}")
        # Don't raise - KPI failures shouldn't break main flow

def track_cycle_start(engine: str) -> None:
    """Track cycle start event"""
    kpi_push("cycle_start", {
        "engine": engine,
        "count": 0,
        "status": "started"
    })

def track_cycle_end(engine: str, count: int, success: bool = True) -> None:
    """Track cycle end event"""
    kpi_push("cycle_end", {
        "engine": engine,
        "count": count,
        "status": "completed" if success else "failed",
        "success": success
    })

def track_error(engine: str, error: str, context: Optional[Dict[str, Any]] = None) -> None:
    """Track error event"""
    error_data = {
        "engine": engine,
        "error": str(error),
        "count": 0,
        "status": "error"
    }
    if context:
        error_data.update(context)
    
    kpi_push("error", error_data)

def track_boot() -> None:
    """Track system boot event"""
    kpi_push("boot", {
        "count": 0,
        "status": "started",
        "components": ["main", "health", "watchdog", "rei_engine", "govcon_engine"]
    })