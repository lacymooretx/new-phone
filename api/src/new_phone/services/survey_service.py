import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.survey import SurveyResponse, SurveyTemplate

logger = structlog.get_logger()


class SurveyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Templates ──────────────────────────────────────────────
    async def list_templates(self, tenant_id: uuid.UUID) -> list[SurveyTemplate]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SurveyTemplate)
            .where(SurveyTemplate.tenant_id == tenant_id)
            .order_by(SurveyTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_template(self, tenant_id: uuid.UUID, template_id: uuid.UUID) -> SurveyTemplate | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(SurveyTemplate).where(
                SurveyTemplate.id == template_id,
                SurveyTemplate.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_template(self, tenant_id: uuid.UUID, **kwargs) -> SurveyTemplate:
        await set_tenant_context(self.db, tenant_id)
        # Convert questions to dicts if they're pydantic models
        if "questions" in kwargs:
            kwargs["questions"] = [q.model_dump() if hasattr(q, "model_dump") else q for q in kwargs["questions"]]
        template = SurveyTemplate(tenant_id=tenant_id, **kwargs)
        self.db.add(template)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def update_template(self, tenant_id: uuid.UUID, template_id: uuid.UUID, **updates) -> SurveyTemplate | None:
        tmpl = await self.get_template(tenant_id, template_id)
        if not tmpl:
            return None
        if "questions" in updates and updates["questions"] is not None:
            updates["questions"] = [q.model_dump() if hasattr(q, "model_dump") else q for q in updates["questions"]]
        for k, v in updates.items():
            if v is not None and hasattr(tmpl, k):
                setattr(tmpl, k, v)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(tmpl)
        return tmpl

    async def delete_template(self, tenant_id: uuid.UUID, template_id: uuid.UUID) -> bool:
        tmpl = await self.get_template(tenant_id, template_id)
        if not tmpl:
            return False
        await self.db.delete(tmpl)
        await self.db.commit()
        return True

    # ── Responses ──────────────────────────────────────────────
    async def list_responses(
        self, tenant_id: uuid.UUID, template_id: uuid.UUID | None = None,
        queue_id: uuid.UUID | None = None, page: int = 1, per_page: int = 50,
    ) -> tuple[list[SurveyResponse], int]:
        await set_tenant_context(self.db, tenant_id)
        query = select(SurveyResponse).where(SurveyResponse.tenant_id == tenant_id)
        count_q = select(func.count(SurveyResponse.id)).where(SurveyResponse.tenant_id == tenant_id)

        if template_id:
            query = query.where(SurveyResponse.template_id == template_id)
            count_q = count_q.where(SurveyResponse.template_id == template_id)
        if queue_id:
            query = query.where(SurveyResponse.queue_id == queue_id)
            count_q = count_q.where(SurveyResponse.queue_id == queue_id)

        total = (await self.db.execute(count_q)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(SurveyResponse.created_at.desc()).offset(offset).limit(per_page)
        )
        return list(result.scalars().all()), total

    async def create_response(self, tenant_id: uuid.UUID, **kwargs) -> SurveyResponse:
        await set_tenant_context(self.db, tenant_id)
        resp = SurveyResponse(tenant_id=tenant_id, completed_at=datetime.now(UTC), **kwargs)
        self.db.add(resp)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(resp)
        return resp

    async def get_analytics(self, tenant_id: uuid.UUID, template_id: uuid.UUID) -> dict:
        await set_tenant_context(self.db, tenant_id)
        tmpl = await self.get_template(tenant_id, template_id)
        if not tmpl:
            raise ValueError("Template not found")

        result = await self.db.execute(
            select(SurveyResponse).where(
                SurveyResponse.tenant_id == tenant_id,
                SurveyResponse.template_id == template_id,
            )
        )
        responses = list(result.scalars().all())

        total = len(responses)
        scores = [r.overall_score for r in responses if r.overall_score is not None]
        avg_score = sum(scores) / len(scores) if scores else None

        per_queue: dict[str, list[float]] = {}
        per_agent: dict[str, list[float]] = {}
        for r in responses:
            if r.overall_score is not None:
                if r.queue_id:
                    per_queue.setdefault(str(r.queue_id), []).append(r.overall_score)
                if r.agent_extension:
                    per_agent.setdefault(r.agent_extension, []).append(r.overall_score)

        return {
            "template_id": str(template_id),
            "template_name": tmpl.name,
            "total_responses": total,
            "avg_overall_score": avg_score,
            "per_question_avg": {},
            "per_queue_avg": {k: sum(v) / len(v) for k, v in per_queue.items()},
            "per_agent_avg": {k: sum(v) / len(v) for k, v in per_agent.items()},
        }
