import math
import uuid
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import Date, Integer, cast, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.queue import Queue
from new_phone.models.workforce_management import (
    WfmForecastConfig,
    WfmScheduleEntry,
    WfmShift,
    WfmTimeOffRequest,
    WfmTimeOffStatus,
)
from new_phone.schemas.workforce_management import (
    WfmForecastConfigCreate,
    WfmScheduleEntryCreate,
    WfmScheduleEntryUpdate,
    WfmShiftCreate,
    WfmShiftUpdate,
    WfmTimeOffRequestCreate,
    WfmTimeOffReview,
)

logger = structlog.get_logger()

# Day-of-week names matching PostgreSQL extract(dow ...) [0=Sunday .. 6=Saturday]
DOW_NAMES = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


class WfmService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Shift CRUD ──

    async def list_shifts(self, tenant_id: uuid.UUID, *, is_active: bool | None = None) -> list[WfmShift]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(WfmShift).where(WfmShift.tenant_id == tenant_id)
        if is_active is not None:
            stmt = stmt.where(WfmShift.is_active == is_active)
        stmt = stmt.order_by(WfmShift.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_shift(self, tenant_id: uuid.UUID, shift_id: uuid.UUID) -> WfmShift | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmShift).where(WfmShift.id == shift_id, WfmShift.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def create_shift(self, tenant_id: uuid.UUID, data: WfmShiftCreate) -> WfmShift:
        await set_tenant_context(self.db, tenant_id)
        # Check unique name
        existing = await self.db.execute(
            select(WfmShift).where(
                WfmShift.tenant_id == tenant_id,
                WfmShift.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Shift '{data.name}' already exists")

        shift = WfmShift(
            tenant_id=tenant_id,
            name=data.name,
            start_time=data.start_time,
            end_time=data.end_time,
            break_minutes=data.break_minutes,
            color=data.color,
        )
        self.db.add(shift)
        await self.db.commit()
        await self.db.refresh(shift)
        return shift

    async def update_shift(self, tenant_id: uuid.UUID, shift_id: uuid.UUID, data: WfmShiftUpdate) -> WfmShift:
        shift = await self.get_shift(tenant_id, shift_id)
        if not shift:
            raise ValueError("Shift not found")

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != shift.name:
            existing = await self.db.execute(
                select(WfmShift).where(
                    WfmShift.tenant_id == tenant_id,
                    WfmShift.name == update_data["name"],
                    WfmShift.id != shift_id,
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Shift '{update_data['name']}' already exists")

        for key, value in update_data.items():
            setattr(shift, key, value)

        await self.db.commit()
        await self.db.refresh(shift)
        return shift

    async def deactivate_shift(self, tenant_id: uuid.UUID, shift_id: uuid.UUID) -> WfmShift:
        shift = await self.get_shift(tenant_id, shift_id)
        if not shift:
            raise ValueError("Shift not found")
        shift.is_active = False
        await self.db.commit()
        await self.db.refresh(shift)
        return shift

    # ── Schedule Entry CRUD ──

    async def list_schedule_entries(
        self,
        tenant_id: uuid.UUID,
        *,
        date_from: date,
        date_to: date,
        extension_id: uuid.UUID | None = None,
    ) -> list[WfmScheduleEntry]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(WfmScheduleEntry)
            .where(
                WfmScheduleEntry.tenant_id == tenant_id,
                WfmScheduleEntry.date >= date_from,
                WfmScheduleEntry.date <= date_to,
            )
            .options(selectinload(WfmScheduleEntry.shift))
        )
        if extension_id is not None:
            stmt = stmt.where(WfmScheduleEntry.extension_id == extension_id)
        stmt = stmt.order_by(WfmScheduleEntry.date, WfmScheduleEntry.extension_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_schedule_entry(self, tenant_id: uuid.UUID, data: WfmScheduleEntryCreate) -> WfmScheduleEntry:
        await set_tenant_context(self.db, tenant_id)
        entry = WfmScheduleEntry(
            tenant_id=tenant_id,
            extension_id=data.extension_id,
            shift_id=data.shift_id,
            date=data.date,
            notes=data.notes,
        )
        self.db.add(entry)
        try:
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise ValueError("Schedule conflict: agent already has a shift on this date") from exc
        await self.db.refresh(entry)
        return entry

    async def bulk_create_schedule_entries(
        self, tenant_id: uuid.UUID, entries: list[WfmScheduleEntryCreate]
    ) -> list[WfmScheduleEntry]:
        await set_tenant_context(self.db, tenant_id)
        created = []
        for data in entries:
            entry = WfmScheduleEntry(
                tenant_id=tenant_id,
                extension_id=data.extension_id,
                shift_id=data.shift_id,
                date=data.date,
                notes=data.notes,
            )
            self.db.add(entry)
            created.append(entry)
        try:
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            raise ValueError("Schedule conflict: one or more agents already have shifts on the specified dates") from exc
        for entry in created:
            await self.db.refresh(entry)
        return created

    async def update_schedule_entry(
        self, tenant_id: uuid.UUID, entry_id: uuid.UUID, data: WfmScheduleEntryUpdate
    ) -> WfmScheduleEntry:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmScheduleEntry).where(
                WfmScheduleEntry.id == entry_id,
                WfmScheduleEntry.tenant_id == tenant_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Schedule entry not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(entry, key, value)

        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_schedule_entry(self, tenant_id: uuid.UUID, entry_id: uuid.UUID) -> None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmScheduleEntry).where(
                WfmScheduleEntry.id == entry_id,
                WfmScheduleEntry.tenant_id == tenant_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise ValueError("Schedule entry not found")
        await self.db.delete(entry)
        await self.db.commit()

    async def get_schedule_overview(
        self, tenant_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)

        # Count scheduled per day
        sched_stmt = (
            select(
                WfmScheduleEntry.date,
                func.count(WfmScheduleEntry.id).label("total_scheduled"),
            )
            .where(
                WfmScheduleEntry.tenant_id == tenant_id,
                WfmScheduleEntry.date >= date_from,
                WfmScheduleEntry.date <= date_to,
            )
            .group_by(WfmScheduleEntry.date)
        )
        sched_result = await self.db.execute(sched_stmt)
        sched_map = {row.date: row.total_scheduled for row in sched_result}

        # Count approved time-off per day (expand date ranges)
        timeoff_stmt = (
            select(WfmTimeOffRequest)
            .where(
                WfmTimeOffRequest.tenant_id == tenant_id,
                WfmTimeOffRequest.status == WfmTimeOffStatus.APPROVED,
                WfmTimeOffRequest.start_date <= date_to,
                WfmTimeOffRequest.end_date >= date_from,
            )
        )
        timeoff_result = await self.db.execute(timeoff_stmt)
        timeoff_map: dict[date, int] = {}
        for req in timeoff_result.scalars():
            d = max(req.start_date, date_from)
            end = min(req.end_date, date_to)
            while d <= end:
                timeoff_map[d] = timeoff_map.get(d, 0) + 1
                d += timedelta(days=1)

        # Build overview
        overview = []
        current = date_from
        while current <= date_to:
            scheduled = sched_map.get(current, 0)
            time_off = timeoff_map.get(current, 0)
            overview.append({
                "date": current,
                "total_scheduled": scheduled,
                "time_off_approved": time_off,
                "net_available": max(scheduled - time_off, 0),
            })
            current += timedelta(days=1)
        return overview

    # ── Time-Off CRUD ──

    async def list_time_off_requests(
        self,
        tenant_id: uuid.UUID,
        *,
        extension_id: uuid.UUID | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[WfmTimeOffRequest]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(WfmTimeOffRequest).where(WfmTimeOffRequest.tenant_id == tenant_id)
        if extension_id is not None:
            stmt = stmt.where(WfmTimeOffRequest.extension_id == extension_id)
        if status is not None:
            stmt = stmt.where(WfmTimeOffRequest.status == status)
        if date_from is not None:
            stmt = stmt.where(WfmTimeOffRequest.end_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(WfmTimeOffRequest.start_date <= date_to)
        stmt = stmt.order_by(WfmTimeOffRequest.start_date.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_time_off_request(
        self, tenant_id: uuid.UUID, data: WfmTimeOffRequestCreate
    ) -> WfmTimeOffRequest:
        await set_tenant_context(self.db, tenant_id)
        if data.end_date < data.start_date:
            raise ValueError("End date must be on or after start date")

        req = WfmTimeOffRequest(
            tenant_id=tenant_id,
            extension_id=data.extension_id,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
            status=WfmTimeOffStatus.PENDING,
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def review_time_off_request(
        self,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        user_id: uuid.UUID,
        review: WfmTimeOffReview,
    ) -> WfmTimeOffRequest:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmTimeOffRequest).where(
                WfmTimeOffRequest.id == request_id,
                WfmTimeOffRequest.tenant_id == tenant_id,
            )
        )
        req = result.scalar_one_or_none()
        if not req:
            raise ValueError("Time-off request not found")
        if req.status != WfmTimeOffStatus.PENDING:
            raise ValueError(f"Request already {req.status}")

        req.status = review.status
        req.reviewed_by_id = user_id
        req.reviewed_at = datetime.now(UTC)
        req.review_notes = review.review_notes

        await self.db.commit()
        await self.db.refresh(req)
        return req

    # ── Forecast Config CRUD ──

    async def list_forecast_configs(self, tenant_id: uuid.UUID) -> list[WfmForecastConfig]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmForecastConfig)
            .where(WfmForecastConfig.tenant_id == tenant_id)
            .order_by(WfmForecastConfig.created_at)
        )
        return list(result.scalars().all())

    async def get_forecast_config(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID
    ) -> WfmForecastConfig | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(WfmForecastConfig).where(
                WfmForecastConfig.tenant_id == tenant_id,
                WfmForecastConfig.queue_id == queue_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_forecast_config(
        self, tenant_id: uuid.UUID, data: WfmForecastConfigCreate
    ) -> WfmForecastConfig:
        await set_tenant_context(self.db, tenant_id)
        existing = await self.get_forecast_config(tenant_id, data.queue_id)
        if existing:
            existing.target_sla_percent = data.target_sla_percent
            existing.target_sla_seconds = data.target_sla_seconds
            existing.shrinkage_percent = data.shrinkage_percent
            existing.lookback_weeks = data.lookback_weeks
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        config = WfmForecastConfig(
            tenant_id=tenant_id,
            queue_id=data.queue_id,
            target_sla_percent=data.target_sla_percent,
            target_sla_seconds=data.target_sla_seconds,
            shrinkage_percent=data.shrinkage_percent,
            lookback_weeks=data.lookback_weeks,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    # ── CDR Analytics ──

    async def get_hourly_volume(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[dict]:
        """Average call volume, AHT, and abandon rate per hour from CDR data."""
        await set_tenant_context(self.db, tenant_id)

        # Count distinct days in the range for averaging
        num_days = (date_to - date_from).days + 1
        if num_days < 1:
            return []

        hour_col = extract("hour", CallDetailRecord.start_time)
        stmt = (
            select(
                hour_col.label("hour"),
                func.count(CallDetailRecord.id).label("total_calls"),
                func.avg(CallDetailRecord.duration_seconds).label("avg_aht"),
                func.sum(
                    func.cast(CallDetailRecord.disposition == "ABANDONED", Integer)
                ).label("abandoned"),
            )
            .where(
                CallDetailRecord.tenant_id == tenant_id,
                CallDetailRecord.queue_id == queue_id,
                cast(CallDetailRecord.start_time, Date) >= date_from,
                cast(CallDetailRecord.start_time, Date) <= date_to,
            )
            .group_by(hour_col)
            .order_by(hour_col)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        hourly = []
        row_map = {int(r.hour): r for r in rows}
        for h in range(24):
            r = row_map.get(h)
            if r:
                total = float(r.total_calls)
                abandoned = float(r.abandoned or 0)
                hourly.append({
                    "hour": h,
                    "avg_calls": round(total / num_days, 2),
                    "avg_aht_seconds": round(float(r.avg_aht or 0), 2),
                    "avg_abandon_rate": round(abandoned / total * 100 if total > 0 else 0, 2),
                })
            else:
                hourly.append({
                    "hour": h,
                    "avg_calls": 0.0,
                    "avg_aht_seconds": 0.0,
                    "avg_abandon_rate": 0.0,
                })
        return hourly

    async def get_daily_volume(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID, date_from: date, date_to: date
    ) -> list[dict]:
        """Average call volume and AHT per day-of-week from CDR data."""
        await set_tenant_context(self.db, tenant_id)

        dow_col = extract("dow", CallDetailRecord.start_time)  # 0=Sunday
        # Count weeks per dow for proper averaging
        num_weeks = max(((date_to - date_from).days + 1) / 7, 1)

        stmt = (
            select(
                dow_col.label("dow"),
                func.count(CallDetailRecord.id).label("total_calls"),
                func.avg(CallDetailRecord.duration_seconds).label("avg_aht"),
            )
            .where(
                CallDetailRecord.tenant_id == tenant_id,
                CallDetailRecord.queue_id == queue_id,
                cast(CallDetailRecord.start_time, Date) >= date_from,
                cast(CallDetailRecord.start_time, Date) <= date_to,
            )
            .group_by(dow_col)
            .order_by(dow_col)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        row_map = {int(r.dow): r for r in rows}
        daily = []
        for dow in range(7):
            r = row_map.get(dow)
            if r:
                daily.append({
                    "day_of_week": DOW_NAMES[dow],
                    "avg_calls": round(float(r.total_calls) / num_weeks, 2),
                    "avg_aht_seconds": round(float(r.avg_aht or 0), 2),
                })
            else:
                daily.append({
                    "day_of_week": DOW_NAMES[dow],
                    "avg_calls": 0.0,
                    "avg_aht_seconds": 0.0,
                })
        return daily

    # ── Erlang C Forecast ──

    async def get_staffing_forecast(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID
    ) -> list[dict]:
        """24-hour staffing forecast using Erlang C formula."""
        config = await self.get_forecast_config(tenant_id, queue_id)
        # Use defaults if no config
        target_sla_pct = config.target_sla_percent if config else 80
        target_sla_sec = config.target_sla_seconds if config else 20
        shrinkage_pct = config.shrinkage_percent if config else 30
        lookback = config.lookback_weeks if config else 8

        date_to = date.today()
        date_from = date_to - timedelta(weeks=lookback)

        hourly_data = await self.get_hourly_volume(tenant_id, queue_id, date_from, date_to)

        forecast = []
        for h_data in hourly_data:
            calls = h_data["avg_calls"]
            aht = h_data["avg_aht_seconds"]
            if calls <= 0 or aht <= 0:
                forecast.append({
                    "hour": h_data["hour"],
                    "predicted_calls": calls,
                    "recommended_agents": 0,
                    "target_sla_percent": target_sla_pct,
                    "target_sla_seconds": target_sla_sec,
                })
                continue

            raw_agents = _compute_agents_needed(calls, aht, target_sla_pct, target_sla_sec)
            # Apply shrinkage
            adjusted = math.ceil(raw_agents / (1 - shrinkage_pct / 100)) if shrinkage_pct < 100 else raw_agents
            forecast.append({
                "hour": h_data["hour"],
                "predicted_calls": calls,
                "recommended_agents": adjusted,
                "target_sla_percent": target_sla_pct,
                "target_sla_seconds": target_sla_sec,
            })
        return forecast

    async def get_staffing_summary(self, tenant_id: uuid.UUID) -> list[dict]:
        """Staffing summary across all queues."""
        await set_tenant_context(self.db, tenant_id)
        # Get all active queues
        queues_result = await self.db.execute(
            select(Queue)
            .where(Queue.tenant_id == tenant_id, Queue.is_active.is_(True))
            .options(selectinload(Queue.members))
        )
        queues = list(queues_result.scalars().all())

        summaries = []
        for queue in queues:
            forecast = await self.get_staffing_forecast(tenant_id, queue.id)
            # Get peak recommendation and total predicted
            max_rec = max((f["recommended_agents"] for f in forecast), default=0)
            total_vol = sum(f["predicted_calls"] for f in forecast)
            current_agents = sum(
                1 for m in queue.members
                if m.extension and m.extension.is_active
                and m.extension.agent_status
                and m.extension.agent_status != "Logged Out"
            )
            summaries.append({
                "queue_id": queue.id,
                "queue_name": queue.name,
                "current_agents": current_agents,
                "recommended_agents": max_rec,
                "forecast_volume": round(total_vol, 2),
            })
        return summaries


# ── Erlang C helper functions ──


def _erlang_c(calls_per_hour: float, aht_seconds: float, num_agents: int) -> float:
    """Probability a call must wait (Erlang C formula)."""
    traffic_intensity = calls_per_hour * aht_seconds / 3600.0  # Erlangs
    if num_agents <= 0 or num_agents <= traffic_intensity:
        return 1.0  # All agents busy

    # Compute Erlang C using iterative approach (avoids factorial overflow)
    # P(wait) = (A^N/N!) * (N/(N-A)) / [sum(A^k/k!, k=0..N-1) + (A^N/N!)*(N/(N-A))]
    a = traffic_intensity
    n = num_agents

    # Compute A^k/k! iteratively
    sum_terms = 0.0
    term = 1.0  # A^0/0! = 1
    for k in range(n):
        sum_terms += term
        term *= a / (k + 1)
    # term is now A^N/N!
    an_nfact = term

    rho = a / n  # Server utilization
    if rho >= 1.0:
        return 1.0

    erlang_c = (an_nfact * n / (n - a)) / (sum_terms + an_nfact * n / (n - a))
    return max(0.0, min(1.0, erlang_c))


def _compute_agents_needed(
    calls_per_hour: float,
    aht_seconds: float,
    target_sla_pct: int,
    target_sla_seconds: int,
) -> int:
    """Find minimum agents meeting SLA target using Erlang C."""
    traffic_intensity = calls_per_hour * aht_seconds / 3600.0
    min_agents = max(1, math.ceil(traffic_intensity))

    for n in range(min_agents, min_agents + 200):
        pw = _erlang_c(calls_per_hour, aht_seconds, n)
        # P(answered within T) = 1 - Pw * e^(-(N-A)*T/AHT)
        a = traffic_intensity
        if n <= a:
            continue
        exponent = -(n - a) * target_sla_seconds / (aht_seconds if aht_seconds > 0 else 1)
        sla_achieved = (1.0 - pw * math.exp(exponent)) * 100
        if sla_achieved >= target_sla_pct:
            return n

    # Fallback: return min_agents + a buffer
    return min_agents + 5
