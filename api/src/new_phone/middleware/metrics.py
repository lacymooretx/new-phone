import re
import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
)

# Custom telephony metrics (updated by ESL event listener / call tracking)
ACTIVE_CALLS = Gauge("active_calls", "Number of active calls")
REGISTERED_EXTENSIONS = Gauge("registered_extensions", "Number of registered SIP extensions")

# UUID pattern compiled once for path normalization
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_NUMERIC_ID_RE = re.compile(r"/\d+(?=/|$)")


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects Prometheus metrics for every HTTP request."""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself to avoid self-instrumentation noise
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = self._normalize_path(request.url.path)

        REQUESTS_IN_PROGRESS.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(method=method, path=path, status=response.status_code).inc()
            return response
        except Exception:
            REQUEST_COUNT.labels(method=method, path=path, status=500).inc()
            raise
        finally:
            duration = time.perf_counter() - start
            REQUEST_DURATION.labels(method=method, path=path).observe(duration)
            REQUESTS_IN_PROGRESS.dec()

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Replace UUIDs and numeric IDs to prevent label cardinality explosion."""
        path = _UUID_RE.sub("{id}", path)
        path = _NUMERIC_ID_RE.sub("/{id}", path)
        return path


async def metrics_endpoint(request: Request) -> Response:
    """Expose Prometheus metrics at /metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
