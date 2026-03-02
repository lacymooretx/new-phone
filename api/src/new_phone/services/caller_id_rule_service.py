import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.caller_id_rule import CallerIdRule
from new_phone.schemas.caller_id_rule import CallerIdRuleCreate, CallerIdRuleUpdate


class CallerIdRuleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_rules(self, tenant_id: uuid.UUID) -> list[CallerIdRule]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(CallerIdRule)
            .where(CallerIdRule.tenant_id == tenant_id, CallerIdRule.is_active.is_(True))
            .order_by(CallerIdRule.priority.desc(), CallerIdRule.name)
        )
        return list(result.scalars().all())

    async def get_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> CallerIdRule | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(CallerIdRule).where(
                CallerIdRule.id == rule_id,
                CallerIdRule.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_rule(self, tenant_id: uuid.UUID, data: CallerIdRuleCreate) -> CallerIdRule:
        await set_tenant_context(self.db, tenant_id)

        existing = await self.db.execute(
            select(CallerIdRule).where(
                CallerIdRule.tenant_id == tenant_id,
                CallerIdRule.name == data.name,
                CallerIdRule.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Caller ID rule '{data.name}' already exists")

        rule = CallerIdRule(
            tenant_id=tenant_id,
            name=data.name,
            rule_type=data.rule_type,
            match_pattern=data.match_pattern,
            action=data.action,
            destination_id=data.destination_id,
            priority=data.priority,
            notes=data.notes,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_rule(
        self, tenant_id: uuid.UUID, rule_id: uuid.UUID, data: CallerIdRuleUpdate
    ) -> CallerIdRule:
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            raise ValueError("Caller ID rule not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def deactivate(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> CallerIdRule:
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            raise ValueError("Caller ID rule not found")
        rule.is_active = False
        await self.db.commit()
        await self.db.refresh(rule)
        return rule
