import json
import re
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.middleware.metrics import (
    FREESWITCH_ACTIVE_CHANNELS,
    FREESWITCH_CALLS_PER_SECOND,
    FREESWITCH_REGISTRATIONS_TOTAL,
    FREESWITCH_SESSIONS_PEAK,
    FREESWITCH_SESSIONS_PEAK_5MIN,
    FREESWITCH_UP,
)
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.extension import Extension
from new_phone.models.user import User
from new_phone.schemas.calls import (
    ActiveCallEntry,
    ActiveCallsResponse,
    FreeSwitchMetrics,
    NumberHistoryEntry,
    OriginateRequest,
    OriginateResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/tenants/{tenant_id}/calls", tags=["calls"])


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _parse_show_channels(raw: str) -> list[dict]:
    """Parse FreeSWITCH 'show channels as json' response into structured dicts."""
    try:
        data = json.loads(raw)
        rows = data.get("rows", [])
        channels = []
        for row in rows:
            channel = {
                "uuid": row.get("uuid", ""),
                "direction": row.get("direction", ""),
                "created": row.get("created", ""),
                "created_epoch": row.get("created_epoch", ""),
                "name": row.get("name", ""),
                "state": row.get("state", ""),
                "cid_name": row.get("cid_name", ""),
                "cid_num": row.get("cid_num", ""),
                "ip_addr": row.get("ip_addr", ""),
                "dest": row.get("dest", ""),
                "application": row.get("application", ""),
                "application_data": row.get("application_data", ""),
                "dialplan": row.get("dialplan", ""),
                "context": row.get("context", ""),
                "read_codec": row.get("read_codec", ""),
                "read_rate": row.get("read_rate", ""),
                "write_codec": row.get("write_codec", ""),
                "write_rate": row.get("write_rate", ""),
                "secure": row.get("secure", ""),
                "hostname": row.get("hostname", ""),
                "presence_id": row.get("presence_id", ""),
                "presence_data": row.get("presence_data", ""),
                "accountcode": row.get("accountcode", ""),
                "callstate": row.get("callstate", ""),
            }
            channels.append(channel)
        return channels
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _parse_status_response(raw: str) -> dict:
    """Parse FreeSWITCH 'status' response to extract session and rate info.

    Example status output:
    UP 0 years, 0 days, 2 hours, 15 minutes, 30 seconds, 123 milliseconds, 456 microseconds
    FreeSWITCH (Version 1.10.11 ...) is ready
    5 session(s) since startup
    3 session(s) - peak 5, last 5min 3
    0 session(s) per Sec out of max 30 per Sec
    1000 session(s) max
    min idle cpu 0.00/97.33
    Current Stack Size/Max 240K/8192K
    """
    metrics = {
        "sessions_since_startup": 0,
        "current_sessions": 0,
        "sessions_peak": 0,
        "sessions_peak_5min": 0,
        "sessions_per_sec": 0.0,
        "sessions_max": 0,
    }

    if not raw:
        return metrics

    for line in raw.split("\n"):
        line = line.strip()

        # "5 session(s) since startup"
        m = re.match(r"(\d+)\s+session\(s\)\s+since\s+startup", line)
        if m:
            metrics["sessions_since_startup"] = int(m.group(1))
            continue

        # "3 session(s) - peak 5, last 5min 3"
        m = re.match(r"(\d+)\s+session\(s\)\s+-\s+peak\s+(\d+),\s+last\s+5min\s+(\d+)", line)
        if m:
            metrics["current_sessions"] = int(m.group(1))
            metrics["sessions_peak"] = int(m.group(2))
            metrics["sessions_peak_5min"] = int(m.group(3))
            continue

        # "0 session(s) per Sec out of max 30 per Sec"
        m = re.match(r"([\d.]+)\s+session\(s\)\s+per\s+Sec\s+out\s+of\s+max\s+(\d+)", line)
        if m:
            metrics["sessions_per_sec"] = float(m.group(1))
            metrics["sessions_max"] = int(m.group(2))
            continue

    return metrics


def _parse_registrations(raw: str) -> int:
    """Parse FreeSWITCH 'show registrations as json' to count active registrations."""
    if not raw:
        return 0
    try:
        data = json.loads(raw)
        return int(data.get("row_count", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0


@router.get("/active", response_model=ActiveCallsResponse)
async def get_active_calls(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
):
    """Get active calls from FreeSWITCH via ESL 'show channels' command."""
    _check_tenant_access(user, tenant_id)

    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FreeSWITCH service unavailable",
        )

    raw = await freeswitch_service._send_command("api show channels as json")
    if not raw:
        return ActiveCallsResponse(total=0, channels=[])

    parsed = _parse_show_channels(raw)

    channels = [
        ActiveCallEntry(
            uuid=ch["uuid"],
            direction=ch["direction"],
            caller_name=ch["cid_name"],
            caller_number=ch["cid_num"],
            destination=ch["dest"],
            state=ch["state"],
            callstate=ch["callstate"],
            read_codec=ch["read_codec"],
            write_codec=ch["write_codec"],
            secure=ch["secure"],
            created=ch["created"],
            created_epoch=ch["created_epoch"],
            hostname=ch["hostname"],
            context=ch["context"],
        )
        for ch in parsed
    ]

    return ActiveCallsResponse(total=len(channels), channels=channels)


@router.get("/metrics/freeswitch", response_model=FreeSwitchMetrics)
async def get_freeswitch_metrics(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
):
    """Get FreeSWITCH metrics and update Prometheus gauges."""
    _check_tenant_access(user, tenant_id)

    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        FREESWITCH_UP.set(0)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FreeSWITCH service unavailable",
        )

    # Fetch status from FreeSWITCH
    status_raw = await freeswitch_service._send_command("api status")
    channels_raw = await freeswitch_service._send_command("api show channels as json")
    registrations_raw = await freeswitch_service._send_command("api show registrations as json")

    if not status_raw:
        FREESWITCH_UP.set(0)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FreeSWITCH not responding",
        )

    FREESWITCH_UP.set(1)

    status_metrics = _parse_status_response(status_raw)
    channel_count = len(_parse_show_channels(channels_raw)) if channels_raw else 0
    reg_count = _parse_registrations(registrations_raw)

    # Update Prometheus gauges
    FREESWITCH_ACTIVE_CHANNELS.set(channel_count)
    FREESWITCH_CALLS_PER_SECOND.set(status_metrics["sessions_per_sec"])
    FREESWITCH_REGISTRATIONS_TOTAL.set(reg_count)
    FREESWITCH_SESSIONS_PEAK.set(status_metrics["sessions_peak"])
    FREESWITCH_SESSIONS_PEAK_5MIN.set(status_metrics["sessions_peak_5min"])

    return FreeSwitchMetrics(
        active_channels=channel_count,
        calls_per_second=status_metrics["sessions_per_sec"],
        registrations_total=reg_count,
        sessions_since_startup=status_metrics["sessions_since_startup"],
        sessions_peak=status_metrics["sessions_peak"],
        sessions_peak_5min=status_metrics["sessions_peak_5min"],
        sessions_max=status_metrics["sessions_max"],
        current_sessions=status_metrics["current_sessions"],
    )


@router.post("/originate", response_model=OriginateResponse)
async def originate_call(
    tenant_id: uuid.UUID,
    body: OriginateRequest,
    user: Annotated[User, Depends(require_permission(Permission.PLACE_CALLS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    """Originate a call: ring the user's device, then bridge to destination."""
    _check_tenant_access(user, tenant_id)

    # Resolve caller extension
    if body.caller_extension_id:
        result = await db.execute(
            select(Extension).where(
                Extension.id == body.caller_extension_id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()
    else:
        result = await db.execute(
            select(Extension).where(
                Extension.user_id == user.id,
                Extension.tenant_id == tenant_id,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()

    if not ext:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension found for this user",
        )

    from new_phone.main import freeswitch_service

    if not freeswitch_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FreeSWITCH service unavailable",
        )

    job_uuid = await freeswitch_service.originate_call(
        ext.sip_username, body.destination, body.originate_timeout
    )

    logger.info(
        "call_originated",
        tenant_id=str(tenant_id),
        user_id=str(user.id),
        extension=ext.extension_number,
        destination=body.destination,
        job_uuid=job_uuid,
    )

    return OriginateResponse(
        status="originating",
        destination=body.destination,
        caller_extension=ext.extension_number,
    )


@router.get("/history", response_model=list[NumberHistoryEntry])
async def get_call_history(
    tenant_id: uuid.UUID,
    number: str,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_CDRS))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    limit: int = 10,
):
    """Get recent call history for a phone number."""
    _check_tenant_access(user, tenant_id)

    if limit > 50:
        limit = 50

    result = await db.execute(
        select(CallDetailRecord)
        .where(
            CallDetailRecord.tenant_id == tenant_id,
            or_(
                CallDetailRecord.caller_number == number,
                CallDetailRecord.called_number == number,
            ),
        )
        .order_by(CallDetailRecord.start_time.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
