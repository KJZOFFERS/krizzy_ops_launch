import time
from prometheus_client import Counter, Histogram

REQUESTS = Counter("ko_requests_total", "Requests", ["route","method","code"])
LATENCY  = Histogram("ko_request_latency_seconds", "Latency", ["route","method"])

def track(route: str, method: str):
    start = time.perf_counter()
    def finalize(code: int):
        LATENCY.labels(route, method).observe(time.perf_counter() - start)
        REQUESTS.labels(route, method, str(code)).inc()
    return finalize
