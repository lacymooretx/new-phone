import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.auth.rbac import Permission, is_msp_role
from new_phone.deps.auth import get_admin_db, require_permission
from new_phone.models.user import User
from new_phone.schemas.compliance_monitoring import (
    ComplianceAgentScore,
    ComplianceEvaluationDetailResponse,
    ComplianceEvaluationResponse,
    ComplianceEvaluationReview,
    ComplianceEvaluationTrigger,
    ComplianceQueueScore,
    ComplianceRuleCreate,
    ComplianceRuleEffectiveness,
    ComplianceRuleResponse,
    ComplianceRuleUpdate,
    ComplianceSummary,
    ComplianceTrendPoint,
)
from new_phone.services.compliance_monitoring_service import ComplianceMonitoringService
from new_phone.services.compliance_scan_service import ComplianceScanService

router = APIRouter(
    prefix="/tenants/{tenant_id}/compliance-monitoring",
    tags=["compliance-monitoring"],
)


def _check_tenant_access(user: User, tenant_id: uuid.UUID) -> None:
    if not is_msp_role(user.role) and user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ── Rules ──


@router.get("/rules", response_model=list[ComplianceRuleResponse])
async def list_rules(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    category: str | None = None,
    scope_type: str | None = None,
    is_active: bool | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    return await service.list_rules(tenant_id, category=category, scope_type=scope_type, is_active=is_active)


@router.post("/rules", response_model=ComplianceRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    tenant_id: uuid.UUID,
    body: ComplianceRuleCreate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    try:
        rule = await service.create_rule(tenant_id, body.model_dump(exclude_unset=True))
        await db.commit()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.get("/rules/{rule_id}", response_model=ComplianceRuleResponse)
async def get_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    rule = await service.get_rule(tenant_id, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


@router.patch("/rules/{rule_id}", response_model=ComplianceRuleResponse)
async def update_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    body: ComplianceRuleUpdate,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    try:
        rule = await service.update_rule(tenant_id, rule_id, body.model_dump(exclude_unset=True))
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
        await db.commit()
        return rule
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from None


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_rule(
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    if not await service.deactivate_rule(tenant_id, rule_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    await db.commit()


# ── Evaluations ──


@router.post("/evaluations", response_model=ComplianceEvaluationResponse, status_code=status.HTTP_201_CREATED)
async def trigger_evaluation(
    tenant_id: uuid.UUID,
    body: ComplianceEvaluationTrigger,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    scan_service = ComplianceScanService(db)
    try:
        evaluation = await scan_service.evaluate(
            tenant_id,
            cdr_id=body.cdr_id,
            ai_conversation_id=body.ai_conversation_id,
        )
        await db.commit()
        return evaluation
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None


@router.get("/evaluations", response_model=list[ComplianceEvaluationResponse])
async def list_evaluations(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    is_flagged: bool | None = None,
    eval_status: Annotated[str | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    return await service.list_evaluations(
        tenant_id,
        is_flagged=is_flagged,
        status=eval_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/evaluations/{evaluation_id}", response_model=ComplianceEvaluationDetailResponse)
async def get_evaluation(
    tenant_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    evaluation = await service.get_evaluation(tenant_id, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return evaluation


@router.patch("/evaluations/{evaluation_id}/review", response_model=ComplianceEvaluationResponse)
async def review_evaluation(
    tenant_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    body: ComplianceEvaluationReview,
    user: Annotated[User, Depends(require_permission(Permission.MANAGE_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    evaluation = await service.review_evaluation(
        tenant_id, evaluation_id, user.id, body.review_notes
    )
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    await db.commit()
    return evaluation


# ── Analytics ──


@router.get("/analytics/summary", response_model=ComplianceSummary)
async def get_analytics_summary(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    data = await service.get_summary(tenant_id, date_from, date_to)
    return ComplianceSummary(**data)


@router.get("/analytics/agent-scores", response_model=list[ComplianceAgentScore])
async def get_agent_scores(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    rows = await service.get_agent_scores(tenant_id, date_from, date_to, limit)
    return [ComplianceAgentScore(**r) for r in rows]


@router.get("/analytics/queue-scores", response_model=list[ComplianceQueueScore])
async def get_queue_scores(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    rows = await service.get_queue_scores(tenant_id, date_from, date_to, limit)
    return [ComplianceQueueScore(**r) for r in rows]


@router.get("/analytics/rule-effectiveness", response_model=list[ComplianceRuleEffectiveness])
async def get_rule_effectiveness(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    rows = await service.get_rule_effectiveness(tenant_id, date_from, date_to)
    return [ComplianceRuleEffectiveness(**r) for r in rows]


@router.get("/analytics/trend", response_model=list[ComplianceTrendPoint])
async def get_trend(
    tenant_id: uuid.UUID,
    user: Annotated[User, Depends(require_permission(Permission.VIEW_COMPLIANCE))],
    db: Annotated[AsyncSession, Depends(get_admin_db)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    granularity: str = Query("daily", pattern=r"^(daily|weekly|monthly)$"),
):
    _check_tenant_access(user, tenant_id)
    service = ComplianceMonitoringService(db)
    rows = await service.get_trend(tenant_id, date_from, date_to, granularity)
    return [ComplianceTrendPoint(**r) for r in rows]
