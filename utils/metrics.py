# utils/metrics.py
import os
from time import perf_counter
from functools import wraps

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "1") not in ("0", "false", "False")

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
except Exception:
    METRICS_ENABLED = False
    # No-op fallbacks
    class _Noop:
        def labels(self, *_, **__): return self
        def inc(self, *_, **__): pass
        def observe(self, *_, **__): pass
    def Counter(*_, **__): return _Noop()
    def Histogram(*_, **__): return _Noop()
    def generate_latest(): return b""
    CONTENT_TYPE_LATEST = "text/plain"

REQS = Counter("krizzy_ops_requests_total", "Total requests", ["endpoint","method","status"])
LAT  = Histogram("krizzy_ops_request_latency_seconds", "Latency seconds", ["endpoint","method"])

def _label(method: str): return method or "NA"

def track(endpoint: str):
    """Decorator: record count + latency. Works for sync or async endpoints."""
    def _wrap(func):
        is_async = hasattr(func, "__call__") and func.__code__.co_flags & 0x80
        @wraps(func)
        async def aw(*args, **kwargs):
            start = perf_counter()
            method = getattr(kwargs.get("request", None), "method", "NA")
            try:
                resp = await func(*args, **kwargs)
                status = getattr(resp, "status_code", 200)
                return resp
            except Exception:
                status = 500
                raise
            finally:
                if METRICS_ENABLED:
                    REQS.labels(endpoint=endpoint, method=_label(method), status=str(status)).inc()
                    LAT.labels(endpoint=endpoint, method=_label(method)).observe(perf_counter() - start)

        @wraps(func)
        def sw(*args, **kwargs):
            start = perf_counter()
            method = getattr(kwargs.get("request", None), "method", "NA")
            try:
                resp = func(*args, **kwargs)
                status = getattr(resp, "status_code", 200)
                return resp
            except Exception:
                status = 500
                raise
            finally:
                if METRICS_ENABLED:
                    REQS.labels(endpoint=endpoint, method=_label(method), status=str(status)).inc()
                    LAT.labels(endpoint=endpoint, method=_label(method)).observe(perf_counter() - start)
        return aw if is_async else sw
    return _wrap

# Expose /metrics payload
def metrics_payload():
    return generate_latest(), CONTENT_TYPE_LATEST
