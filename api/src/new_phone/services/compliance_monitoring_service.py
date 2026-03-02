import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.compliance_monitoring import (
    ComplianceEvaluation,
    ComplianceRule,
    ComplianceRuleResult,
)
from new_phone.models.extension import Extension
from new_phone.models.queue import Queue


class ComplianceMonitoringService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Rule CRUD ──

    async def list_rules(
        self,
        tenant_id: uuid.UUID,
        *,
        category: str | None = None,
        scope_type: str | None = None,
        is_active: bool | None = None,
    ) -> list[ComplianceRule]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(ComplianceRule).where(ComplianceRule.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(ComplianceRule.category == category)
        if scope_type:
            stmt = stmt.where(ComplianceRule.scope_type == scope_type)
        if is_active is not None:
            stmt = stmt.where(ComplianceRule.is_active == is_active)
        stmt = stmt.order_by(ComplianceRule.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> ComplianceRule | None:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(ComplianceRule).where(
            ComplianceRule.tenant_id == tenant_id,
            ComplianceRule.id == rule_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_rule(self, tenant_id: uuid.UUID, data: dict) -> ComplianceRule:
        await set_tenant_context(self.db, tenant_id)
        # Check unique name within tenant
        existing = await self.db.execute(
            select(ComplianceRule).where(
                ComplianceRule.tenant_id == tenant_id,
                ComplianceRule.name == data["name"],
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Rule with name '{data['name']}' already exists")
        rule = ComplianceRule(tenant_id=tenant_id, **data)
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def update_rule(
        self, tenant_id: uuid.UUID, rule_id: uuid.UUID, data: dict
    ) -> ComplianceRule | None:
        await set_tenant_context(self.db, tenant_id)
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            return None
        # Check unique name if changing
        if "name" in data and data["name"] != rule.name:
            existing = await self.db.execute(
                select(ComplianceRule).where(
                    ComplianceRule.tenant_id == tenant_id,
                    ComplianceRule.name == data["name"],
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Rule with name '{data['name']}' already exists")
        for key, value in data.items():
            if value is not None:
                setattr(rule, key, value)
        await self.db.flush()
        await self.db.refresh(rule)
        return rule

    async def deactivate_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        await set_tenant_context(self.db, tenant_id)
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            return False
        rule.is_active = False
        await self.db.flush()
        return True

    # ── Evaluation CRUD ──

    async def list_evaluations(
        self,
        tenant_id: uuid.UUID,
        *,
        is_flagged: bool | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ComplianceEvaluation]:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(ComplianceEvaluation).where(
            ComplianceEvaluation.tenant_id == tenant_id
        )
        if is_flagged is not None:
            stmt = stmt.where(ComplianceEvaluation.is_flagged == is_flagged)
        if status:
            stmt = stmt.where(ComplianceEvaluation.status == status)
        if date_from:
            stmt = stmt.where(ComplianceEvaluation.evaluated_at >= date_from)
        if date_to:
            stmt = stmt.where(ComplianceEvaluation.evaluated_at <= date_to)
        stmt = stmt.order_by(ComplianceEvaluation.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_evaluation(
        self, tenant_id: uuid.UUID, evaluation_id: uuid.UUID
    ) -> ComplianceEvaluation | None:
        await set_tenant_context(self.db, tenant_id)
        stmt = select(ComplianceEvaluation).where(
            ComplianceEvaluation.tenant_id == tenant_id,
            ComplianceEvaluation.id == evaluation_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def review_evaluation(
        self,
        tenant_id: uuid.UUID,
        evaluation_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str | None = None,
    ) -> ComplianceEvaluation | None:
        await set_tenant_context(self.db, tenant_id)
        evaluation = await self.get_evaluation(tenant_id, evaluation_id)
        if not evaluation:
            return None
        evaluation.status = "reviewed"
        evaluation.reviewed_by_id = user_id
        evaluation.reviewed_at = datetime.now(UTC)
        evaluation.review_notes = notes
        await self.db.flush()
        await self.db.refresh(evaluation)
        return evaluation

    # ── Analytics ──

    @staticmethod
    def _default_range() -> tuple[datetime, datetime]:
        now = datetime.now(UTC)
        return now - timedelta(days=30), now

    async def get_summary(
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

        CE = ComplianceEvaluation
        stmt = select(
            func.count().label("total_evaluations"),
            func.avg(CE.overall_score).label("average_score"),
            func.count(case((CE.is_flagged.is_(True), 1))).label("flagged_count"),
        ).where(
            CE.tenant_id == tenant_id,
            CE.created_at >= date_from,
            CE.created_at <= date_to,
            CE.status != "pending",
        )
        result = await self.db.execute(stmt)
        row = result.one()

        total = row.total_evaluations or 0
        flagged = row.flagged_count or 0

        # Status breakdown
        status_stmt = (
            select(CE.status, func.count().label("cnt"))
            .where(
                CE.tenant_id == tenant_id,
                CE.created_at >= date_from,
                CE.created_at <= date_to,
            )
            .group_by(CE.status)
        )
        status_result = await self.db.execute(status_stmt)
        status_breakdown = {r.status: r.cnt for r in status_result.all()}

        # Pass rate: evaluations where is_flagged is False / total completed
        completed = status_breakdown.get("completed", 0) + status_breakdown.get("reviewed", 0)
        pass_stmt = select(func.count()).where(
            CE.tenant_id == tenant_id,
            CE.created_at >= date_from,
            CE.created_at <= date_to,
            CE.status.in_(["completed", "reviewed"]),
            CE.is_flagged.is_(False),
        )
        pass_result = await self.db.execute(pass_stmt)
        pass_count = pass_result.scalar() or 0

        return {
            "total_evaluations": total,
            "average_score": float(row.average_score) if row.average_score else None,
            "flagged_count": flagged,
            "flagged_rate": round(flagged / total * 100, 2) if total > 0 else 0.0,
            "pass_rate": round(pass_count / completed * 100, 2) if completed > 0 else 0.0,
            "status_breakdown": status_breakdown,
        }

    async def get_agent_scores(
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

        CE = ComplianceEvaluation
        CDR = CallDetailRecord
        stmt = (
            select(
                Extension.id.label("extension_id"),
                Extension.extension_number,
                func.count().label("evaluation_count"),
                func.avg(CE.overall_score).label("average_score"),
                func.count(case((CE.is_flagged.is_(True), 1))).label("flagged_count"),
            )
            .join(CDR, CE.cdr_id == CDR.id)
            .join(Extension, CDR.extension_id == Extension.id)
            .where(
                CE.tenant_id == tenant_id,
                CE.created_at >= date_from,
                CE.created_at <= date_to,
                CE.status.in_(["completed", "reviewed"]),
                CDR.extension_id.is_not(None),
            )
            .group_by(Extension.id, Extension.extension_number)
            .order_by(func.avg(CE.overall_score).asc().nulls_last())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "extension_id": r.extension_id,
                "extension_number": r.extension_number,
                "evaluation_count": r.evaluation_count,
                "average_score": float(r.average_score) if r.average_score else None,
                "flagged_count": r.flagged_count,
            }
            for r in result.all()
        ]

    async def get_queue_scores(
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

        CE = ComplianceEvaluation
        CDR = CallDetailRecord
        stmt = (
            select(
                Queue.id.label("queue_id"),
                Queue.name.label("queue_name"),
                func.count().label("evaluation_count"),
                func.avg(CE.overall_score).label("average_score"),
                func.count(case((CE.is_flagged.is_(True), 1))).label("flagged_count"),
            )
            .join(CDR, CE.cdr_id == CDR.id)
            .join(Queue, CDR.queue_id == Queue.id)
            .where(
                CE.tenant_id == tenant_id,
                CE.created_at >= date_from,
                CE.created_at <= date_to,
                CE.status.in_(["completed", "reviewed"]),
                CDR.queue_id.is_not(None),
            )
            .group_by(Queue.id, Queue.name)
            .order_by(func.avg(CE.overall_score).asc().nulls_last())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "queue_id": r.queue_id,
                "queue_name": r.queue_name,
                "evaluation_count": r.evaluation_count,
                "average_score": float(r.average_score) if r.average_score else None,
                "flagged_count": r.flagged_count,
            }
            for r in result.all()
        ]

    async def get_rule_effectiveness(
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

        CRR = ComplianceRuleResult
        CR = ComplianceRule
        stmt = (
            select(
                CR.id.label("rule_id"),
                CR.name.label("rule_name"),
                CR.severity,
                func.count().label("total_evaluated"),
                func.count(case((CRR.result == "pass", 1))).label("pass_count"),
                func.count(case((CRR.result == "fail", 1))).label("fail_count"),
                func.count(case((CRR.result == "not_applicable", 1))).label("not_applicable_count"),
            )
            .join(CR, CRR.rule_id == CR.id)
            .where(
                CRR.tenant_id == tenant_id,
                CRR.created_at >= date_from,
                CRR.created_at <= date_to,
            )
            .group_by(CR.id, CR.name, CR.severity)
            .order_by(func.count(case((CRR.result == "fail", 1))).desc())
        )
        result = await self.db.execute(stmt)
        return [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "severity": r.severity,
                "total_evaluated": r.total_evaluated,
                "pass_count": r.pass_count,
                "fail_count": r.fail_count,
                "not_applicable_count": r.not_applicable_count,
                "fail_rate": round(r.fail_count / r.total_evaluated * 100, 2) if r.total_evaluated > 0 else 0.0,
            }
            for r in result.all()
        ]

    async def get_trend(
        self,
        tenant_id: uuid.UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        granularity: str = "daily",
    ) -> list[dict]:
        await set_tenant_context(self.db, tenant_id)
        if not date_from:
            date_from, _ = self._default_range()
        if not date_to:
            _, date_to = self._default_range()

        CE = ComplianceEvaluation

        if granularity == "weekly":
            period_expr = func.to_char(
                func.date_trunc("week", CE.created_at), "IYYY-IW"
            )
        elif granularity == "monthly":
            period_expr = func.to_char(CE.created_at, "YYYY-MM")
        else:  # daily
            period_expr = func.to_char(CE.created_at, "YYYY-MM-DD")

        stmt = (
            select(
                period_expr.label("period"),
                func.count().label("evaluation_count"),
                func.avg(CE.overall_score).label("average_score"),
                func.count(case((CE.is_flagged.is_(True), 1))).label("flagged_count"),
            )
            .where(
                CE.tenant_id == tenant_id,
                CE.created_at >= date_from,
                CE.created_at <= date_to,
                CE.status.in_(["completed", "reviewed"]),
            )
            .group_by(period_expr)
            .order_by(period_expr)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "period": r.period,
                "evaluation_count": r.evaluation_count,
                "average_score": float(r.average_score) if r.average_score else None,
                "flagged_count": r.flagged_count,
            }
            for r in result.all()
        ]
