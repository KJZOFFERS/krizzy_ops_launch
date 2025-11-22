import time
import requests
from typing import Optional, Tuple, Any


def http_get_retry(url: str, max_retries: int = 3, timeout: int = 25) -> Optional[requests.Response]:
    for attempt in range(max_retries):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return None


def get_json_retry(url: str, max_retries: int = 3, timeout: int = 25) -> Tuple[int, Any]:
    r = http_get_retry(url, max_retries=max_retries, timeout=timeout)
    if not r:
        return 0, {}
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def get_text_retry(url: str, max_retries: int = 3, timeout: int = 25) -> Tuple[int, str]:
    r = http_get_retry(url, max_retries=max_retries, timeout=timeout)
    if not r:
        return 0, ""
    return r.status_code, r.text
