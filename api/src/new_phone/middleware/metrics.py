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

# FreeSWITCH-specific metrics
FREESWITCH_ACTIVE_CHANNELS = Gauge(
    "freeswitch_active_channels",
    "Number of active FreeSWITCH channels",
)
FREESWITCH_CALLS_PER_SECOND = Gauge(
    "freeswitch_calls_per_second",
    "Current calls per second rate in FreeSWITCH",
)
FREESWITCH_REGISTRATIONS_TOTAL = Gauge(
    "freeswitch_registrations_total",
    "Total number of active SIP registrations in FreeSWITCH",
)
FREESWITCH_SESSIONS_PEAK = Gauge(
    "freeswitch_sessions_peak",
    "Peak session count since FreeSWITCH started",
)
FREESWITCH_SESSIONS_PEAK_5MIN = Gauge(
    "freeswitch_sessions_peak_5min",
    "Peak session count in the last 5 minutes",
)
FREESWITCH_UP = Gauge(
    "freeswitch_up",
    "Whether FreeSWITCH is reachable (1=up, 0=down)",
)

# SMS metrics
SMS_SENDS_TOTAL = Counter(
    "sms_sends_total",
    "Total SMS messages sent",
    ["provider", "status"],
)
SMS_DELIVERY_FAILURES_TOTAL = Counter(
    "sms_delivery_failures_total",
    "Total SMS delivery failures",
    ["provider"],
)

# Queue metrics
QUEUE_WAIT_TIME = Histogram(
    "queue_wait_time_seconds",
    "Time callers wait in queue before being answered",
    ["queue_name"],
    buckets=(10, 30, 60, 120, 180, 300, 600),
)

# SIP trunk metrics
SIP_TRUNK_REGISTERED = Gauge(
    "sip_trunk_registered",
    "Whether a SIP trunk is registered (1=yes, 0=no)",
    ["trunk_name"],
)

# DB connection pool metrics
DB_POOL_AVAILABLE = Gauge(
    "db_pool_available_connections",
    "Number of available database connections in the pool",
)
DB_POOL_IN_USE = Gauge(
    "db_pool_in_use_connections",
    "Number of database connections currently in use",
)

# Recording archive metrics
RECORDING_ARCHIVE_LAST_SUCCESS = Gauge(
    "recording_archive_last_success_timestamp",
    "Timestamp of the last successful recording archive job",
)

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
