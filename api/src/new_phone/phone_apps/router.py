"""Desk phone XML app endpoints — unauthenticated, MAC-based auth.

Serves XML pages for Yealink, Polycom, and Cisco desk phone screens.
Pattern matches provisioning/router.py (AdminSessionLocal, no JWT).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Form, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from new_phone.db.engine import AdminSessionLocal
from new_phone.db.rls import set_tenant_context
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.extension import Extension
from new_phone.models.parking_lot import ParkingLot
from new_phone.models.queue import Queue, QueueMember
from new_phone.models.voicemail_message import VoicemailMessage
from new_phone.phone_apps.auth import resolve_phone_context
from new_phone.phone_apps.renderers import (
    DirEntry,
    MenuItem,
    PageInfo,
    StatusRow,
    render_directory,
    render_input_screen,
    render_menu,
    render_status_list,
    render_text_screen,
)
from new_phone.config import settings
from new_phone.phone_apps.service import PhoneAppConfigService

logger = structlog.get_logger()

router = APIRouter(tags=["phone-apps"])


def _base_url(mac: str) -> str:
    """Return the full external base URL for phone app endpoints."""
    return f"{settings.provisioning_base_url.rstrip('/')}/phone-apps/{mac}"

XML = "text/xml; charset=ISO-8859-1"


def _xml(content: str) -> Response:
    return Response(content=content, media_type=XML)


def _error(manufacturer: str, msg: str, code: int = 404) -> Response:
    return Response(
        content=render_text_screen(manufacturer or "yealink", "Error", msg),
        status_code=code,
        media_type=XML,
    )


def _not_found() -> Response:
    return Response(content="Device not found", status_code=status.HTTP_404_NOT_FOUND)


# ── 1. Main Menu ────────────────────────────────────────────────────


@router.get("/phone-apps/{mac}/menu")
async def phone_menu(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        svc = PhoneAppConfigService(session)
        config = await svc.get_or_create(ctx.tenant.id)
        await session.commit()

    base = _base_url(ctx.mac)
    company = config.company_name or ctx.tenant.name or "Phone Apps"

    items: list[MenuItem] = []
    if config.directory_enabled:
        items.append(MenuItem("Directory", f"{base}/directory"))
    if config.voicemail_enabled and ctx.extension.voicemail_box_id:
        items.append(MenuItem("Voicemail", f"{base}/voicemail"))
    if config.call_history_enabled:
        items.append(MenuItem("Call History", f"{base}/history"))
    if config.parking_enabled:
        items.append(MenuItem("Parking", f"{base}/parking"))
    if config.queue_dashboard_enabled:
        items.append(MenuItem("Queues", f"{base}/queues"))
    if config.settings_enabled:
        items.append(MenuItem("Settings", f"{base}/settings"))

    return _xml(render_menu(ctx.manufacturer, company, items))


# ── 2. Directory ────────────────────────────────────────────────────


@router.get("/phone-apps/{mac}/directory")
async def phone_directory(
    mac: str, q: str = Query("", max_length=50), page: int = Query(1, ge=1)
) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        svc = PhoneAppConfigService(session)
        config = await svc.get_or_create(ctx.tenant.id)
        await session.commit()

    page_size = config.page_size
    offset = (page - 1) * page_size

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        stmt = (
            select(Extension)
            .where(Extension.tenant_id == ctx.tenant.id, Extension.is_active.is_(True))
            .order_by(Extension.extension_number)
        )
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                Extension.internal_cid_name.ilike(pattern)
                | Extension.extension_number.like(pattern)
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await session.execute(count_stmt)).scalar() or 0

        # Fetch page
        stmt = stmt.offset(offset).limit(page_size)
        result = await session.execute(stmt)
        extensions = list(result.scalars().all())

    entries = [
        DirEntry(
            name=ext.internal_cid_name or f"Ext {ext.extension_number}",
            number=ext.extension_number,
        )
        for ext in extensions
    ]

    base_url = f"{_base_url(ctx.mac)}/directory"
    if q:
        base_url = f"{base_url}?q={q}"

    page_info = PageInfo(page=page, page_size=page_size, total=total)

    return _xml(render_directory(ctx.manufacturer, "Directory", entries, page_info, base_url))


# ── 3. Directory Search ────────────────────────────────────────────


@router.get("/phone-apps/{mac}/directory/search")
async def phone_directory_search(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    return _xml(
        render_input_screen(
            ctx.manufacturer,
            "Search Directory",
            "Enter name or number",
            f"{_base_url(ctx.mac)}/directory",
            "q",
        )
    )


# ── 4. Voicemail List ──────────────────────────────────────────────


@router.get("/phone-apps/{mac}/voicemail")
async def phone_voicemail(mac: str, page: int = Query(1, ge=1)) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    if not ctx.extension.voicemail_box_id:
        return _error(ctx.manufacturer, "No voicemail box configured")

    async with AdminSessionLocal() as session:
        svc = PhoneAppConfigService(session)
        config = await svc.get_or_create(ctx.tenant.id)
        await session.commit()

    page_size = config.page_size
    offset = (page - 1) * page_size

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)

        # Count total
        count_stmt = select(func.count()).where(
            VoicemailMessage.tenant_id == ctx.tenant.id,
            VoicemailMessage.voicemail_box_id == ctx.extension.voicemail_box_id,
            VoicemailMessage.is_active.is_(True),
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        # Fetch page
        stmt = (
            select(VoicemailMessage)
            .where(
                VoicemailMessage.tenant_id == ctx.tenant.id,
                VoicemailMessage.voicemail_box_id == ctx.extension.voicemail_box_id,
                VoicemailMessage.is_active.is_(True),
            )
            .order_by(VoicemailMessage.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        messages = list(result.scalars().all())

    base = _base_url(ctx.mac)
    items: list[MenuItem] = []
    for msg in messages:
        caller = msg.caller_name or msg.caller_number or "Unknown"
        duration = msg.duration_seconds or 0
        flag = "NEW" if not msg.is_read else "read"
        label = f"{caller} - {duration}s ({flag})"
        items.append(MenuItem(label, f"{base}/voicemail/{msg.id}"))

    page_info = PageInfo(page=page, page_size=page_size, total=total)

    # Render as menu with pagination
    xml = render_menu(ctx.manufacturer, "Voicemail", items)
    # For voicemail we add pagination via status list since render_menu doesn't paginate
    # Instead, let's use directory format which supports pagination
    if page_info.total_pages > 1:
        entries = [DirEntry(name=item.prompt, number="") for item in items]
        return _xml(
            render_directory(
                ctx.manufacturer,
                f"Voicemail (Page {page}/{page_info.total_pages})",
                entries,
                page_info,
                f"{base}/voicemail",
            )
        )

    return _xml(xml)


# ── 5. Voicemail Detail ────────────────────────────────────────────


@router.get("/phone-apps/{mac}/voicemail/{message_id}")
async def phone_voicemail_detail(mac: str, message_id: uuid.UUID) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    if not ctx.extension.voicemail_box_id:
        return _error(ctx.manufacturer, "No voicemail box configured")

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        result = await session.execute(
            select(VoicemailMessage).where(
                VoicemailMessage.id == message_id,
                VoicemailMessage.tenant_id == ctx.tenant.id,
                VoicemailMessage.voicemail_box_id == ctx.extension.voicemail_box_id,
                VoicemailMessage.is_active.is_(True),
            )
        )
        msg = result.scalar_one_or_none()

    if not msg:
        return _error(ctx.manufacturer, "Message not found")

    caller = msg.caller_name or "Unknown"
    number = msg.caller_number or "Unknown"
    duration = msg.duration_seconds or 0
    time_str = msg.created_at.strftime("%Y-%m-%d %H:%M") if msg.created_at else ""
    status_str = "New" if not msg.is_read else "Read"
    urgent = " [URGENT]" if msg.is_urgent else ""

    text = (
        f"From: {caller} ({number})\n"
        f"Duration: {duration}s\n"
        f"Received: {time_str}\n"
        f"Status: {status_str}{urgent}"
    )

    return _xml(render_text_screen(ctx.manufacturer, "Voicemail Detail", text))


# ── 6. Call History ─────────────────────────────────────────────────


@router.get("/phone-apps/{mac}/history")
async def phone_call_history(mac: str, page: int = Query(1, ge=1)) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        svc = PhoneAppConfigService(session)
        config = await svc.get_or_create(ctx.tenant.id)
        await session.commit()

    page_size = config.page_size
    offset = (page - 1) * page_size
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)

        base_where = [
            CallDetailRecord.tenant_id == ctx.tenant.id,
            CallDetailRecord.extension_id == ctx.extension.id,
            CallDetailRecord.start_time >= seven_days_ago,
        ]

        # Count
        count_stmt = select(func.count()).where(*base_where)
        total = (await session.execute(count_stmt)).scalar() or 0

        # Fetch
        stmt = (
            select(CallDetailRecord)
            .where(*base_where)
            .order_by(CallDetailRecord.start_time.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        cdrs = list(result.scalars().all())

    direction_arrows = {"inbound": "<-", "outbound": "->", "internal": "<>"}

    entries: list[DirEntry] = []
    for cdr in cdrs:
        arrow = direction_arrows.get(cdr.direction, "--")
        name = cdr.caller_name or cdr.caller_number or "Unknown"
        if cdr.direction == "outbound":
            name = cdr.called_number or "Unknown"
        disp = (cdr.disposition or "").replace("_", " ")
        time_str = cdr.start_time.strftime("%m/%d %H:%M") if cdr.start_time else ""
        label = f"{arrow} {name} ({disp}) {time_str}"

        # Number to dial back
        dial_number = cdr.caller_number if cdr.direction == "inbound" else cdr.called_number
        entries.append(DirEntry(name=label, number=dial_number or ""))

    page_info = PageInfo(page=page, page_size=page_size, total=total)
    base = f"{_base_url(ctx.mac)}/history"

    return _xml(render_directory(ctx.manufacturer, "Call History", entries, page_info, base))


# ── 7. Parking Panel ───────────────────────────────────────────────


@router.get("/phone-apps/{mac}/parking")
async def phone_parking(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        stmt = (
            select(ParkingLot)
            .where(ParkingLot.tenant_id == ctx.tenant.id, ParkingLot.is_active.is_(True))
            .order_by(ParkingLot.lot_number)
        )
        result = await session.execute(stmt)
        lots = list(result.scalars().all())

    if not lots:
        return _xml(render_text_screen(ctx.manufacturer, "Parking", "No parking lots configured"))

    rows: list[StatusRow] = []
    for lot in lots:
        lot_label = lot.name or f"Lot {lot.lot_number}"
        slots = lot.slot_end - lot.slot_start + 1
        rows.append(
            StatusRow(
                label=lot_label,
                value=f"Slots {lot.slot_start}-{lot.slot_end} ({slots} slots)",
                dial_uri=f"tel:*{lot.slot_start}",
            )
        )

    return _xml(render_status_list(ctx.manufacturer, "Parking", rows))


# ── 8. Queue Dashboard ─────────────────────────────────────────────


@router.get("/phone-apps/{mac}/queues")
async def phone_queues(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        stmt = (
            select(Queue)
            .where(Queue.tenant_id == ctx.tenant.id, Queue.is_active.is_(True))
            .options(selectinload(Queue.members))
            .order_by(Queue.name)
        )
        result = await session.execute(stmt)
        queues = list(result.scalars().all())

    # Filter to queues where this extension is a member
    my_queues = [q for q in queues if any(m.extension_id == ctx.extension.id for m in q.members)]

    if not my_queues:
        return _xml(render_text_screen(ctx.manufacturer, "Queues", "Not a member of any queue"))

    base = _base_url(ctx.mac)
    rows: list[StatusRow] = []
    for q in my_queues:
        member_count = len(q.members)
        label = q.name or f"Queue {q.queue_number}"
        rows.append(
            StatusRow(
                label=label,
                value=f"{member_count} agents",
                dial_uri=f"{base}/queues/{q.id}",
            )
        )

    return _xml(render_status_list(ctx.manufacturer, "Queues", rows))


# ── 9. Queue Detail ────────────────────────────────────────────────


@router.get("/phone-apps/{mac}/queues/{queue_id}")
async def phone_queue_detail(mac: str, queue_id: uuid.UUID) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        result = await session.execute(
            select(Queue)
            .where(
                Queue.id == queue_id,
                Queue.tenant_id == ctx.tenant.id,
                Queue.is_active.is_(True),
            )
            .options(selectinload(Queue.members).selectinload(QueueMember.extension))
        )
        queue = result.scalar_one_or_none()

    if not queue:
        return _error(ctx.manufacturer, "Queue not found")

    lines = [
        f"Queue: {queue.name}",
        f"Number: {queue.queue_number}",
        f"Strategy: {queue.strategy}",
        f"Members: {len(queue.members)}",
        "",
    ]
    for member in queue.members:
        ext = member.extension
        if ext:
            name = ext.internal_cid_name or f"Ext {ext.extension_number}"
            ext_num = ext.extension_number
            lines.append(f"  {name} ({ext_num}) - L{member.level}/P{member.position}")

    return _xml(render_text_screen(ctx.manufacturer, "Queue Detail", "\n".join(lines)))


# ── 10. Settings Menu ──────────────────────────────────────────────


@router.get("/phone-apps/{mac}/settings")
async def phone_settings(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    ext = ctx.extension
    base = f"{_base_url(ctx.mac)}/settings"

    items: list[MenuItem] = []

    # DND toggle
    dnd_status = "ON" if ext.dnd_enabled else "OFF"
    items.append(MenuItem(f"DND: {dnd_status} (toggle)", f"{base}/dnd"))

    # Call forwarding info
    if ext.call_forward_unconditional:
        items.append(
            MenuItem(
                f"Fwd All: {ext.call_forward_unconditional}",
                f"{base}/forward/clear?type=unconditional",
            )
        )
    if ext.call_forward_busy:
        items.append(
            MenuItem(f"Fwd Busy: {ext.call_forward_busy}", f"{base}/forward/clear?type=busy")
        )
    if ext.call_forward_no_answer:
        items.append(
            MenuItem(
                f"Fwd No Answer: {ext.call_forward_no_answer}",
                f"{base}/forward/clear?type=no_answer",
            )
        )

    items.append(MenuItem("Set Forward", f"{base}/forward/set"))
    items.append(MenuItem("Clear All Forwards", f"{base}/forward/clear?type=all"))

    return _xml(render_menu(ctx.manufacturer, "Settings", items))


# ── 11. Toggle DND ─────────────────────────────────────────────────


@router.post("/phone-apps/{mac}/settings/dnd")
async def phone_toggle_dnd(mac: str) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        result = await session.execute(
            select(Extension).where(
                Extension.id == ctx.extension.id,
                Extension.tenant_id == ctx.tenant.id,
            )
        )
        ext = result.scalar_one_or_none()
        if not ext:
            return _error(ctx.manufacturer, "Extension not found")

        ext.dnd_enabled = not ext.dnd_enabled
        new_state = "ON" if ext.dnd_enabled else "OFF"
        await session.commit()

    logger.info(
        "phone_apps_dnd_toggled", mac=mac, dnd=new_state, ext=ctx.extension.extension_number
    )
    return _xml(render_text_screen(ctx.manufacturer, "DND", f"Do Not Disturb is now {new_state}"))


# ── 12. Set Call Forward ────────────────────────────────────────────


@router.get("/phone-apps/{mac}/settings/forward/set")
async def phone_forward_form(mac: str) -> Response:
    """Show input form for setting call forwarding."""
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    base = f"{_base_url(ctx.mac)}/settings"
    items = [
        MenuItem("Forward All Calls", f"{base}/forward/set/unconditional"),
        MenuItem("Forward on Busy", f"{base}/forward/set/busy"),
        MenuItem("Forward on No Answer", f"{base}/forward/set/no_answer"),
    ]
    return _xml(render_menu(ctx.manufacturer, "Set Forward", items))


@router.get("/phone-apps/{mac}/settings/forward/set/{fwd_type}")
async def phone_forward_input(mac: str, fwd_type: str) -> Response:
    """Show input screen for entering forward destination."""
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    valid_types = {"unconditional", "busy", "no_answer"}
    if fwd_type not in valid_types:
        return _error(ctx.manufacturer, "Invalid forward type")

    labels = {
        "unconditional": "Forward All Calls",
        "busy": "Forward on Busy",
        "no_answer": "Forward on No Answer",
    }

    return _xml(
        render_input_screen(
            ctx.manufacturer,
            labels[fwd_type],
            "Enter destination number",
            f"{_base_url(ctx.mac)}/settings/forward?type={fwd_type}",
            "destination",
        )
    )


@router.post("/phone-apps/{mac}/settings/forward")
@router.get("/phone-apps/{mac}/settings/forward")
async def phone_set_forward(
    mac: str,
    type: str = Query("unconditional"),
    destination: str = Query(""),
) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    valid_types = {"unconditional", "busy", "no_answer"}
    if type not in valid_types:
        return _error(ctx.manufacturer, "Invalid forward type")

    if not destination:
        return _error(ctx.manufacturer, "Destination required")

    field_map = {
        "unconditional": "call_forward_unconditional",
        "busy": "call_forward_busy",
        "no_answer": "call_forward_no_answer",
    }

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        result = await session.execute(
            select(Extension).where(
                Extension.id == ctx.extension.id,
                Extension.tenant_id == ctx.tenant.id,
            )
        )
        ext = result.scalar_one_or_none()
        if not ext:
            return _error(ctx.manufacturer, "Extension not found")

        setattr(ext, field_map[type], destination)
        await session.commit()

    logger.info(
        "phone_apps_forward_set",
        mac=mac,
        type=type,
        destination=destination,
        ext=ctx.extension.extension_number,
    )
    return _xml(
        render_text_screen(
            ctx.manufacturer, "Forward Set", f"Forwarding ({type}) set to {destination}"
        )
    )


# ── 13. Clear Call Forward ──────────────────────────────────────────


@router.post("/phone-apps/{mac}/settings/forward/clear")
@router.get("/phone-apps/{mac}/settings/forward/clear")
async def phone_clear_forward(mac: str, type: str = Query("all")) -> Response:
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return _not_found()

    valid_types = {"all", "unconditional", "busy", "no_answer"}
    if type not in valid_types:
        return _error(ctx.manufacturer, "Invalid forward type")

    async with AdminSessionLocal() as session:
        await set_tenant_context(session, ctx.tenant.id)
        result = await session.execute(
            select(Extension).where(
                Extension.id == ctx.extension.id,
                Extension.tenant_id == ctx.tenant.id,
            )
        )
        ext = result.scalar_one_or_none()
        if not ext:
            return _error(ctx.manufacturer, "Extension not found")

        if type == "all":
            ext.call_forward_unconditional = None
            ext.call_forward_busy = None
            ext.call_forward_no_answer = None
        else:
            field_map = {
                "unconditional": "call_forward_unconditional",
                "busy": "call_forward_busy",
                "no_answer": "call_forward_no_answer",
            }
            setattr(ext, field_map[type], None)

        await session.commit()

    logger.info(
        "phone_apps_forward_cleared", mac=mac, type=type, ext=ctx.extension.extension_number
    )
    label = "All forwarding" if type == "all" else f"Forwarding ({type})"
    return _xml(render_text_screen(ctx.manufacturer, "Forward Cleared", f"{label} cleared"))


# ── 14. Action URL ──────────────────────────────────────────────────


@router.post("/phone-apps/{mac}/action-url")
async def phone_action_url(
    mac: str,
    event: str = Form(""),
    call_id: str = Form(""),
    local: str = Form(""),
    remote: str = Form(""),
) -> Response:
    """Receive Yealink phone events (action URL callbacks).

    Logs the event for future extensibility (CRM lookups, push notifications, etc.)
    """
    ctx = await resolve_phone_context(mac)
    if not ctx:
        return Response(status_code=status.HTTP_200_OK)

    logger.info(
        "phone_apps_action_url",
        mac=mac,
        event=event,
        call_id=call_id,
        local=local,
        remote=remote,
        ext=ctx.extension.extension_number,
    )

    return Response(status_code=status.HTTP_200_OK)
