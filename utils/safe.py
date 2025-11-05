# utils/safe.py
import os
import logging
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def make_client():
    """Return a requests Session with reasonable defaults"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'KrizzyOps/1.0'
    })
    return session

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def request_with_retries(func, service="api"):
    """
    Wrapper that retries a function that makes HTTP requests
    func should be a callable that returns a Response object
    """
    try:
        response = func()
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"{service} request failed: {e}")
        raise
