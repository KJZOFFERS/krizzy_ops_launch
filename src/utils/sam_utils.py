# src/utils/sam_utils.py

import os
from typing import Dict, Any, List, Tuple

from ..common.http_utils import get_json_retry

SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "").strip()


def fetch_sam_opportunities(extra_params: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetch opportunities from SAM.gov API.
    
    Returns: (opportunities, meta)
    where meta = {"status": int, "detail": str, "total": int}
    """
    if not SAM_SEARCH_API:
        return [], {"status": 0, "detail": "SAM_SEARCH_API not configured", "total": 0}
    
    url = SAM_SEARCH_API
    if extra_params:
        import urllib.parse
        params_str = urllib.parse.urlencode(extra_params)
        url = f"{url}?{params_str}" if "?" not in url else f"{url}&{params_str}"
    
    status, data = get_json_retry(url, max_retries=3, timeout=30)
    
    meta = {
        "status": status,
        "detail": "",
        "total": 0,
    }
    
    if status == 0:
        meta["detail"] = "Connection failed or timeout"
        return [], meta
    
    if status != 200:
        meta["detail"] = f"HTTP {status}: {str(data)[:500]}"
        return [], meta
    
    # Handle various SAM.gov response formats
    opportunities = []
    if isinstance(data, list):
        opportunities = data
    elif isinstance(data, dict):
        # Try common keys
        for key in ["opportunitiesData", "notices", "results", "data", "opportunities"]:
            if key in data and isinstance(data[key], list):
                opportunities = data[key]
                break
        
        # Extract total count if available
        for key in ["totalRecords", "total", "count", "numFound"]:
            if key in data and isinstance(data[key], (int, str)):
                try:
                    meta["total"] = int(data[key])
                except:
                    pass
    
    meta["detail"] = f"Fetched {len(opportunities)} opportunities"
    meta["total"] = meta.get("total") or len(opportunities)
    
    return opportunities, meta
