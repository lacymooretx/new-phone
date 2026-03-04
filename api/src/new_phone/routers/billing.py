import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission
from new_phone.deps.auth import get_db_with_tenant, require_permission
from new_phone.models.user import User
from new_phone.schemas.billing import (
    BillingConfigResponse,
    BillingConfigUpdate,
    RateDeckCreate,
    RateDeckEntryCreate,
    RateDeckEntryResponse,
    RateDeckResponse,
    RateDeckUpdate,
    RateLookupResponse,
    UsageRecordCreate,
    UsageRecordResponse,
)
from new_phone.services.billing_service import BillingService

router = APIRouter(prefix="/tenants/{tenant_id}/billing", tags=["billing"])


# ── Usage Records ─────────────────────────────────────────


@router.get("/usage", response_model=list[UsageRecordResponse])
async def list_usage_records(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    period_start: Annotated[datetime | None, Query()] = None,
    period_end: Annotated[datetime | None, Query()] = None,
    metric: Annotated[str | None, Query()] = None,
):
    service = BillingService(db)
    return await service.list_usage_records(tenant_id, period_start, period_end, metric)


@router.post("/usage", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_usage_record(
    tenant_id: uuid.UUID,
    data: UsageRecordCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    return await service.create_usage_record(tenant_id, **data.model_dump())


# ── Rate Decks ────────────────────────────────────────────


@router.get("/rate-decks", response_model=list[RateDeckResponse])
async def list_rate_decks(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    return await service.list_rate_decks(tenant_id)


@router.post("/rate-decks", response_model=RateDeckResponse, status_code=status.HTTP_201_CREATED)
async def create_rate_deck(
    tenant_id: uuid.UUID,
    data: RateDeckCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    return await service.create_rate_deck(tenant_id, **data.model_dump())


@router.get("/rate-decks/{rate_deck_id}", response_model=RateDeckResponse)
async def get_rate_deck(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    deck = await service.get_rate_deck(tenant_id, rate_deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Rate deck not found")
    return deck


@router.put("/rate-decks/{rate_deck_id}", response_model=RateDeckResponse)
async def update_rate_deck(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    data: RateDeckUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    deck = await service.update_rate_deck(tenant_id, rate_deck_id, **data.model_dump(exclude_unset=True))
    if not deck:
        raise HTTPException(status_code=404, detail="Rate deck not found")
    return deck


@router.delete("/rate-decks/{rate_deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rate_deck(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    deleted = await service.delete_rate_deck(tenant_id, rate_deck_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rate deck not found")


# ── Rate Deck Entries ─────────────────────────────────────


@router.get("/rate-decks/{rate_deck_id}/entries", response_model=list[RateDeckEntryResponse])
async def list_rate_deck_entries(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    return await service.list_rate_deck_entries(tenant_id, rate_deck_id)


@router.post(
    "/rate-decks/{rate_deck_id}/entries",
    response_model=RateDeckEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_rate_deck_entry(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    data: RateDeckEntryCreate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    try:
        return await service.create_rate_deck_entry(tenant_id, rate_deck_id, **data.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.delete("/rate-deck-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rate_deck_entry(
    tenant_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    deleted = await service.delete_rate_deck_entry(tenant_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rate deck entry not found")


# ── Rate Lookup ───────────────────────────────────────────


@router.get("/rate-decks/{rate_deck_id}/lookup", response_model=RateLookupResponse)
async def lookup_rate(
    tenant_id: uuid.UUID,
    rate_deck_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
    dialed_number: Annotated[str, Query(min_length=1)] = ...,
):
    service = BillingService(db)
    try:
        entry = await service.lookup_rate(tenant_id, rate_deck_id, dialed_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    if not entry:
        return RateLookupResponse(
            dialed_number=dialed_number,
            matched_prefix=None,
            destination=None,
            per_minute_rate=None,
            connection_fee=None,
            minimum_seconds=None,
        )
    return RateLookupResponse(
        dialed_number=dialed_number,
        matched_prefix=entry.prefix,
        destination=entry.destination,
        per_minute_rate=entry.per_minute_rate,
        connection_fee=entry.connection_fee,
        minimum_seconds=entry.minimum_seconds,
    )


# ── Billing Config ────────────────────────────────────────


@router.get("/config", response_model=BillingConfigResponse)
async def get_billing_config(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    config = await service.get_billing_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Billing config not found")
    return config


@router.put("/config", response_model=BillingConfigResponse)
async def update_billing_config(
    tenant_id: uuid.UUID,
    data: BillingConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db_with_tenant)],
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_TENANT))],
):
    service = BillingService(db)
    return await service.update_billing_config(tenant_id, **data.model_dump(exclude_unset=True))
