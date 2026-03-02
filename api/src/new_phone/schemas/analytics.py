import uuid

from pydantic import BaseModel


class CallSummary(BaseModel):
    total_calls: int = 0
    inbound: int = 0
    outbound: int = 0
    internal: int = 0
    answered: int = 0
    no_answer: int = 0
    busy: int = 0
    failed: int = 0
    voicemail: int = 0
    cancelled: int = 0
    avg_duration_seconds: float = 0.0
    total_duration_seconds: int = 0


class CallVolumeTrendPoint(BaseModel):
    period: str
    total: int = 0
    inbound: int = 0
    outbound: int = 0
    internal: int = 0


class CallVolumeTrendResponse(BaseModel):
    granularity: str
    data: list[CallVolumeTrendPoint]


class ExtensionActivity(BaseModel):
    extension_id: uuid.UUID
    extension_number: str
    extension_name: str | None = None
    total_calls: int = 0
    inbound: int = 0
    outbound: int = 0
    missed: int = 0
    avg_duration_seconds: float = 0.0
    total_duration_seconds: int = 0


class DIDUsage(BaseModel):
    did_id: uuid.UUID
    number: str
    total_calls: int = 0
    answered: int = 0
    missed: int = 0
    avg_duration_seconds: float = 0.0


class DurationBucket(BaseModel):
    bucket: str
    count: int = 0
    percentage: float = 0.0


class TopCaller(BaseModel):
    caller_number: str
    caller_name: str | None = None
    total_calls: int = 0
    total_duration_seconds: int = 0
    avg_duration_seconds: float = 0.0


class HourlyDistributionPoint(BaseModel):
    hour: int
    total: int = 0
    inbound: int = 0
    outbound: int = 0


class TenantOverview(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    total_calls: int = 0
    calls_today: int = 0
    extension_count: int = 0


class MSPOverviewResponse(BaseModel):
    total_tenants: int = 0
    total_calls_today: int = 0
    total_calls_week: int = 0
    total_extensions: int = 0
    system_health: str = "unknown"
    tenants: list[TenantOverview] = []
