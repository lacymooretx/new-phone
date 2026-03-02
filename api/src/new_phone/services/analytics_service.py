"""Analytics service — CDR aggregation queries, tenant-scoped with RLS."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, case, cast, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.did import DID
from new_phone.models.extension import Extension
from new_phone.models.tenant import Tenant


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _default_range() -> tuple[datetime, datetime]:
        now = datetime.now(UTC)
        return now - timedelta(days=7), now

    # ── Call Summary ──────────────────────────────────────────────

    async def get_call_summary(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord
        stmt = select(
            func.count().label("total_calls"),
            func.count(case((CDR.direction == "inbound", 1))).label("inbound"),
            func.count(case((CDR.direction == "outbound", 1))).label("outbound"),
            func.count(case((CDR.direction == "internal", 1))).label("internal"),
            func.count(case((CDR.disposition == "answered", 1))).label("answered"),
            func.count(case((CDR.disposition == "no_answer", 1))).label("no_answer"),
            func.count(case((CDR.disposition == "busy", 1))).label("busy"),
            func.count(case((CDR.disposition == "failed", 1))).label("failed"),
            func.count(case((CDR.disposition == "voicemail", 1))).label("voicemail"),
            func.count(case((CDR.disposition == "cancelled", 1))).label("cancelled"),
            func.coalesce(func.avg(CDR.duration_seconds), 0).label("avg_duration_seconds"),
            func.coalesce(func.sum(CDR.duration_seconds), 0).label("total_duration_seconds"),
        ).where(
            CDR.tenant_id == tenant_id,
            CDR.start_time >= date_from,
            CDR.start_time <= date_to,
        )
        result = await self.db.execute(stmt)
        row = result.one()
        return {
            "total_calls": row.total_calls,
            "inbound": row.inbound,
            "outbound": row.outbound,
            "internal": row.internal,
            "answered": row.answered,
            "no_answer": row.no_answer,
            "busy": row.busy,
            "failed": row.failed,
            "voicemail": row.voicemail,
            "cancelled": row.cancelled,
            "avg_duration_seconds": float(row.avg_duration_seconds),
            "total_duration_seconds": int(row.total_duration_seconds),
        }

    # ── Call Volume Trend ─────────────────────────────────────────

    async def get_call_volume_trend(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        granularity: str = "daily",
    ) -> dict:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        if granularity == "hourly":
            period_expr = func.date_trunc("hour", CDR.start_time).label("period")
        else:
            # daily (default)
            period_expr = cast(CDR.start_time, Date).label("period")

        stmt = (
            select(
                period_expr,
                func.count().label("total"),
                func.count(case((CDR.direction == "inbound", 1))).label("inbound"),
                func.count(case((CDR.direction == "outbound", 1))).label("outbound"),
                func.count(case((CDR.direction == "internal", 1))).label("internal"),
            )
            .where(
                CDR.tenant_id == tenant_id,
                CDR.start_time >= date_from,
                CDR.start_time <= date_to,
            )
            .group_by(period_expr)
            .order_by(period_expr)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        data = []
        for row in rows:
            period_val = row.period
            if granularity == "hourly":
                period_str = period_val.isoformat() if hasattr(period_val, "isoformat") else str(period_val)
            else:
                period_str = period_val.isoformat() if hasattr(period_val, "isoformat") else str(period_val)

            data.append({
                "period": period_str,
                "total": row.total,
                "inbound": row.inbound,
                "outbound": row.outbound,
                "internal": row.internal,
            })

        return {"granularity": granularity, "data": data}

    # ── Extension Activity ────────────────────────────────────────

    async def get_extension_activity(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        stmt = (
            select(
                Extension.id.label("extension_id"),
                Extension.extension_number,
                Extension.internal_cid_name.label("extension_name"),
                func.count().label("total_calls"),
                func.count(case((CDR.direction == "inbound", 1))).label("inbound"),
                func.count(case((CDR.direction == "outbound", 1))).label("outbound"),
                func.count(
                    case(
                        (
                            (CDR.disposition == "no_answer") | (CDR.disposition == "cancelled"),
                            1,
                        )
                    )
                ).label("missed"),
                func.coalesce(func.avg(CDR.duration_seconds), 0).label("avg_duration_seconds"),
                func.coalesce(func.sum(CDR.duration_seconds), 0).label("total_duration_seconds"),
            )
            .join(Extension, CDR.extension_id == Extension.id)
            .where(
                CDR.tenant_id == tenant_id,
                CDR.start_time >= date_from,
                CDR.start_time <= date_to,
                CDR.extension_id.is_not(None),
            )
            .group_by(Extension.id, Extension.extension_number, Extension.internal_cid_name)
            .order_by(func.count().desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "extension_id": row.extension_id,
                "extension_number": row.extension_number,
                "extension_name": row.extension_name,
                "total_calls": row.total_calls,
                "inbound": row.inbound,
                "outbound": row.outbound,
                "missed": row.missed,
                "avg_duration_seconds": float(row.avg_duration_seconds),
                "total_duration_seconds": int(row.total_duration_seconds),
            }
            for row in rows
        ]

    # ── DID Usage ─────────────────────────────────────────────────

    async def get_did_usage(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        total_label = func.count().label("total_calls")
        answered_label = func.count(case((CDR.disposition == "answered", 1))).label("answered")

        stmt = (
            select(
                DID.id.label("did_id"),
                DID.number,
                total_label,
                answered_label,
                func.coalesce(func.avg(CDR.duration_seconds), 0).label("avg_duration_seconds"),
            )
            .join(DID, CDR.did_id == DID.id)
            .where(
                CDR.tenant_id == tenant_id,
                CDR.start_time >= date_from,
                CDR.start_time <= date_to,
                CDR.did_id.is_not(None),
            )
            .group_by(DID.id, DID.number)
            .order_by(func.count().desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "did_id": row.did_id,
                "number": row.number,
                "total_calls": row.total_calls,
                "answered": row.answered,
                "missed": row.total_calls - row.answered,
                "avg_duration_seconds": float(row.avg_duration_seconds),
            }
            for row in rows
        ]

    # ── Duration Distribution ─────────────────────────────────────

    async def get_duration_distribution(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        stmt = select(
            func.count(case((CDR.duration_seconds < 30, 1))).label("under_30s"),
            func.count(
                case(((CDR.duration_seconds >= 30) & (CDR.duration_seconds < 60), 1))
            ).label("s30_to_1m"),
            func.count(
                case(((CDR.duration_seconds >= 60) & (CDR.duration_seconds < 300), 1))
            ).label("m1_to_5m"),
            func.count(
                case(((CDR.duration_seconds >= 300) & (CDR.duration_seconds < 900), 1))
            ).label("m5_to_15m"),
            func.count(
                case(((CDR.duration_seconds >= 900) & (CDR.duration_seconds < 1800), 1))
            ).label("m15_to_30m"),
            func.count(case((CDR.duration_seconds >= 1800, 1))).label("over_30m"),
            func.count().label("total"),
        ).where(
            CDR.tenant_id == tenant_id,
            CDR.start_time >= date_from,
            CDR.start_time <= date_to,
        )

        result = await self.db.execute(stmt)
        row = result.one()
        total = row.total or 1  # avoid division by zero

        buckets = [
            ("< 30s", row.under_30s),
            ("30s - 1m", row.s30_to_1m),
            ("1 - 5m", row.m1_to_5m),
            ("5 - 15m", row.m5_to_15m),
            ("15 - 30m", row.m15_to_30m),
            ("30m+", row.over_30m),
        ]

        return [
            {
                "bucket": label,
                "count": count,
                "percentage": round(count / total * 100, 2),
            }
            for label, count in buckets
        ]

    # ── Top Callers ───────────────────────────────────────────────

    async def get_top_callers(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 20,
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        stmt = (
            select(
                CDR.caller_number,
                func.max(CDR.caller_name).label("caller_name"),
                func.count().label("total_calls"),
                func.coalesce(func.sum(CDR.duration_seconds), 0).label("total_duration_seconds"),
                func.coalesce(func.avg(CDR.duration_seconds), 0).label("avg_duration_seconds"),
            )
            .where(
                CDR.tenant_id == tenant_id,
                CDR.direction == "inbound",
                CDR.start_time >= date_from,
                CDR.start_time <= date_to,
            )
            .group_by(CDR.caller_number)
            .order_by(func.count().desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "caller_number": row.caller_number,
                "caller_name": row.caller_name or None,
                "total_calls": row.total_calls,
                "total_duration_seconds": int(row.total_duration_seconds),
                "avg_duration_seconds": float(row.avg_duration_seconds),
            }
            for row in rows
        ]

    # ── Hourly Distribution ───────────────────────────────────────

    async def get_hourly_distribution(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CDR = CallDetailRecord

        stmt = (
            select(
                extract("hour", CDR.start_time).label("hour"),
                func.count().label("total"),
                func.count(case((CDR.direction == "inbound", 1))).label("inbound"),
                func.count(case((CDR.direction == "outbound", 1))).label("outbound"),
            )
            .where(
                CDR.tenant_id == tenant_id,
                CDR.start_time >= date_from,
                CDR.start_time <= date_to,
            )
            .group_by(extract("hour", CDR.start_time))
            .order_by(extract("hour", CDR.start_time))
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build a full 24-hour map, filling missing hours with zeros
        hour_map: dict[int, dict] = {h: {"hour": h, "total": 0, "inbound": 0, "outbound": 0} for h in range(24)}
        for row in rows:
            h = int(row.hour)
            hour_map[h] = {
                "hour": h,
                "total": row.total,
                "inbound": row.inbound,
                "outbound": row.outbound,
            }

        return [hour_map[h] for h in range(24)]

    # ── MSP Overview (no RLS — admin only) ───────────────────────

    async def get_msp_overview(self) -> dict:
        """Cross-tenant overview for MSP admins. No RLS context set."""
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        CDR = CallDetailRecord

        # Active tenant count
        tenant_result = await self.db.execute(
            select(func.count()).where(Tenant.is_active.is_(True))
        )
        total_tenants = tenant_result.scalar() or 0

        # CDRs today
        today_result = await self.db.execute(
            select(func.count()).where(CDR.start_time >= today_start)
        )
        total_calls_today = today_result.scalar() or 0

        # CDRs this week
        week_result = await self.db.execute(
            select(func.count()).where(CDR.start_time >= week_start)
        )
        total_calls_week = week_result.scalar() or 0

        # Total extensions
        ext_result = await self.db.execute(
            select(func.count()).select_from(Extension).where(Extension.is_active.is_(True))
        )
        total_extensions = ext_result.scalar() or 0

        # Per-tenant overview
        tenant_rows_result = await self.db.execute(
            select(Tenant.id, Tenant.name).where(Tenant.is_active.is_(True)).order_by(Tenant.name)
        )
        tenant_rows = tenant_rows_result.all()

        # Calls today per tenant
        today_per_tenant_result = await self.db.execute(
            select(CDR.tenant_id, func.count().label("cnt"))
            .where(CDR.start_time >= today_start)
            .group_by(CDR.tenant_id)
        )
        today_per_tenant = {row.tenant_id: row.cnt for row in today_per_tenant_result.all()}

        # Total calls per tenant
        total_per_tenant_result = await self.db.execute(
            select(CDR.tenant_id, func.count().label("cnt")).group_by(CDR.tenant_id)
        )
        total_per_tenant = {row.tenant_id: row.cnt for row in total_per_tenant_result.all()}

        # Extension count per tenant
        ext_per_tenant_result = await self.db.execute(
            select(Extension.tenant_id, func.count().label("cnt"))
            .where(Extension.is_active.is_(True))
            .group_by(Extension.tenant_id)
        )
        ext_per_tenant = {row.tenant_id: row.cnt for row in ext_per_tenant_result.all()}

        tenants = [
            {
                "tenant_id": row.id,
                "tenant_name": row.name,
                "total_calls": total_per_tenant.get(row.id, 0),
                "calls_today": today_per_tenant.get(row.id, 0),
                "extension_count": ext_per_tenant.get(row.id, 0),
            }
            for row in tenant_rows
        ]

        return {
            "total_tenants": total_tenants,
            "total_calls_today": total_calls_today,
            "total_calls_week": total_calls_week,
            "total_extensions": total_extensions,
            "system_health": "healthy",
            "tenants": tenants,
        }
