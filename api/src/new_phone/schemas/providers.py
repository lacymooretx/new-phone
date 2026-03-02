"""Pydantic schemas for telephony provider operations."""

from pydantic import BaseModel, ConfigDict, Field


class DIDSearchRequest(BaseModel):
    """Query parameters for searching available DIDs."""

    area_code: str | None = Field(None, max_length=10, description="NPA area code filter")
    state: str | None = Field(None, max_length=2, description="US state code (e.g. TX)")
    quantity: int = Field(10, ge=1, le=100, description="Max results to return")


class DIDSearchResultSchema(BaseModel):
    """A single available DID returned from a provider search."""

    model_config = ConfigDict(from_attributes=True)

    number: str
    monthly_cost: float
    setup_cost: float
    provider: str
    capabilities: dict


class DIDPurchaseRequest(BaseModel):
    """Request body to purchase a specific DID."""

    number: str = Field(..., min_length=2, max_length=20, description="E.164 number to purchase")
    provider: str = Field(..., description="Provider to purchase from (clearlyip or twilio)")


class DIDPurchaseResultSchema(BaseModel):
    """Result of a DID purchase."""

    model_config = ConfigDict(from_attributes=True)

    number: str
    provider_sid: str
    provider: str


class DIDRoutingUpdate(BaseModel):
    """Request body to configure DID routing destination."""

    destination_type: str = Field(
        ..., description="Routing target type: extension, ring_group, queue, ivr, voicemail"
    )
    destination_id: str = Field(..., description="UUID of the routing target")


class TrunkProvisionRequestSchema(BaseModel):
    """Request body to provision a new SIP trunk via a provider."""

    name: str = Field(..., min_length=1, max_length=255)
    provider: str = Field(..., description="Provider type (clearlyip or twilio)")
    region: str = Field("us-east", max_length=50, description="Provider region")
    channels: int = Field(30, ge=1, le=9999)
    config: dict = Field(default_factory=dict, description="Provider-specific config")


class TrunkProvisionResultSchema(BaseModel):
    """Result of provisioning a SIP trunk."""

    model_config = ConfigDict(from_attributes=True)

    provider_trunk_id: str
    host: str
    port: int
    username: str
    password: str


class TrunkTestResultSchema(BaseModel):
    """Result of a SIP trunk health-check."""

    model_config = ConfigDict(from_attributes=True)

    status: str
    latency_ms: float | None
    error: str | None
