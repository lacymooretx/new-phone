import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from new_phone.db.rls import set_tenant_context
from new_phone.models.port_request import (
    PortRequest,
    PortRequestHistory,
    PortRequestStatus,
)
from new_phone.schemas.port_requests import PortRequestCreate, PortRequestUpdate

logger = structlog.get_logger()

# Valid status transitions
VALID_TRANSITIONS: dict[str, set[str]] = {
    PortRequestStatus.SUBMITTED: {
        PortRequestStatus.PENDING_LOA,
        PortRequestStatus.CANCELLED,
        PortRequestStatus.REJECTED,
    },
    PortRequestStatus.PENDING_LOA: {
        PortRequestStatus.LOA_SUBMITTED,
        PortRequestStatus.CANCELLED,
        PortRequestStatus.REJECTED,
    },
    PortRequestStatus.LOA_SUBMITTED: {
        PortRequestStatus.FOC_RECEIVED,
        PortRequestStatus.REJECTED,
        PortRequestStatus.CANCELLED,
    },
    PortRequestStatus.FOC_RECEIVED: {
        PortRequestStatus.IN_PROGRESS,
        PortRequestStatus.CANCELLED,
        PortRequestStatus.REJECTED,
    },
    PortRequestStatus.IN_PROGRESS: {
        PortRequestStatus.COMPLETED,
        PortRequestStatus.REJECTED,
    },
    PortRequestStatus.COMPLETED: set(),
    PortRequestStatus.REJECTED: {
        PortRequestStatus.SUBMITTED,  # Allow re-submission
    },
    PortRequestStatus.CANCELLED: set(),
}


class PortService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_port_requests(
        self, tenant_id: uuid.UUID, *, status_filter: str | None = None
    ) -> list[PortRequest]:
        await set_tenant_context(self.db, tenant_id)
        stmt = (
            select(PortRequest)
            .where(PortRequest.tenant_id == tenant_id)
            .order_by(PortRequest.created_at.desc())
        )
        if status_filter:
            stmt = stmt.where(PortRequest.status == status_filter)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_port_request(
        self, tenant_id: uuid.UUID, port_request_id: uuid.UUID
    ) -> PortRequest | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(PortRequest).where(
                PortRequest.id == port_request_id,
                PortRequest.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def submit_port_request(
        self,
        tenant_id: uuid.UUID,
        data: PortRequestCreate,
        submitted_by: uuid.UUID | None = None,
    ) -> PortRequest:
        await set_tenant_context(self.db, tenant_id)

        # Validate all numbers are E.164 format
        for number in data.numbers:
            if not number.startswith("+") or not number[1:].isdigit():
                raise ValueError(
                    f"Number '{number}' is not in E.164 format (must start with + followed by digits)"
                )

        # Check for duplicate port requests with active status
        active_statuses = {
            PortRequestStatus.SUBMITTED,
            PortRequestStatus.PENDING_LOA,
            PortRequestStatus.LOA_SUBMITTED,
            PortRequestStatus.FOC_RECEIVED,
            PortRequestStatus.IN_PROGRESS,
        }
        existing = await self.db.execute(
            select(PortRequest).where(
                PortRequest.tenant_id == tenant_id,
                PortRequest.status.in_(active_statuses),
            )
        )
        existing_requests = list(existing.scalars().all())

        # Check if any of the requested numbers are already in an active port request
        for req in existing_requests:
            overlap = set(data.numbers) & set(req.numbers)
            if overlap:
                raise ValueError(
                    f"Numbers {list(overlap)} are already in an active port request ({req.id})"
                )

        port_request = PortRequest(
            tenant_id=tenant_id,
            numbers=data.numbers,
            current_carrier=data.current_carrier,
            provider=data.provider,
            status=PortRequestStatus.SUBMITTED,
            requested_port_date=data.requested_port_date,
            notes=data.notes,
            submitted_by=submitted_by,
        )
        self.db.add(port_request)
        await self.db.flush()

        # Create initial history entry
        history = PortRequestHistory(
            port_request_id=port_request.id,
            previous_status=None,
            new_status=PortRequestStatus.SUBMITTED,
            changed_by=submitted_by,
            notes="Port request submitted",
        )
        self.db.add(history)

        await self.db.commit()
        await self.db.refresh(port_request)

        logger.info(
            "port_request_submitted",
            tenant_id=str(tenant_id),
            port_request_id=str(port_request.id),
            numbers=data.numbers,
            provider=data.provider,
        )
        return port_request

    async def update_port_request(
        self,
        tenant_id: uuid.UUID,
        port_request_id: uuid.UUID,
        data: PortRequestUpdate,
        changed_by: uuid.UUID | None = None,
    ) -> PortRequest:
        port_request = await self.get_port_request(tenant_id, port_request_id)
        if not port_request:
            raise ValueError("Port request not found")

        if port_request.status in (
            PortRequestStatus.COMPLETED,
            PortRequestStatus.CANCELLED,
        ):
            raise ValueError(
                f"Cannot update port request in '{port_request.status}' status"
            )

        update_data = data.model_dump(exclude_unset=True)

        # Handle status transition separately
        new_status = update_data.pop("status", None)
        if new_status and new_status != port_request.status:
            await self._transition_status(
                port_request, new_status, changed_by, data.notes
            )

        for key, value in update_data.items():
            setattr(port_request, key, value)

        await self.db.commit()
        await self.db.refresh(port_request)
        return port_request

    async def upload_loa(
        self,
        tenant_id: uuid.UUID,
        port_request_id: uuid.UUID,
        loa_file_path: str,
        changed_by: uuid.UUID | None = None,
    ) -> PortRequest:
        port_request = await self.get_port_request(tenant_id, port_request_id)
        if not port_request:
            raise ValueError("Port request not found")

        if port_request.status not in (
            PortRequestStatus.SUBMITTED,
            PortRequestStatus.PENDING_LOA,
        ):
            raise ValueError(
                f"Cannot upload LOA when port request is in '{port_request.status}' status"
            )

        port_request.loa_file_path = loa_file_path

        # Transition to LOA_SUBMITTED
        await self._transition_status(
            port_request,
            PortRequestStatus.LOA_SUBMITTED,
            changed_by,
            "LOA document uploaded",
        )

        await self.db.commit()
        await self.db.refresh(port_request)

        logger.info(
            "port_request_loa_uploaded",
            port_request_id=str(port_request_id),
            loa_file_path=loa_file_path,
        )
        return port_request

    async def check_status(
        self,
        tenant_id: uuid.UUID,
        port_request_id: uuid.UUID,
        changed_by: uuid.UUID | None = None,
    ) -> PortRequest:
        """Poll the provider API for the current status of the port request.

        In a real implementation this would call the ClearlyIP or Twilio API.
        For now, it logs the check and returns the current state.
        """
        port_request = await self.get_port_request(tenant_id, port_request_id)
        if not port_request:
            raise ValueError("Port request not found")

        if port_request.status in (
            PortRequestStatus.COMPLETED,
            PortRequestStatus.CANCELLED,
        ):
            return port_request

        # In production, this would call the provider API:
        #   if port_request.provider == "clearlyip":
        #       status = await clearlyip_client.check_port_status(port_request.provider_port_id)
        #   elif port_request.provider == "twilio":
        #       status = await twilio_client.check_port_status(port_request.provider_port_id)

        logger.info(
            "port_request_status_checked",
            port_request_id=str(port_request_id),
            provider=port_request.provider,
            provider_port_id=port_request.provider_port_id,
            current_status=port_request.status,
        )

        return port_request

    async def cancel_port(
        self,
        tenant_id: uuid.UUID,
        port_request_id: uuid.UUID,
        changed_by: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> PortRequest:
        port_request = await self.get_port_request(tenant_id, port_request_id)
        if not port_request:
            raise ValueError("Port request not found")

        if port_request.status in (
            PortRequestStatus.COMPLETED,
            PortRequestStatus.CANCELLED,
        ):
            raise ValueError(
                f"Cannot cancel port request in '{port_request.status}' status"
            )

        notes = reason or "Port request cancelled by user"
        await self._transition_status(
            port_request, PortRequestStatus.CANCELLED, changed_by, notes
        )

        await self.db.commit()
        await self.db.refresh(port_request)

        logger.info(
            "port_request_cancelled",
            port_request_id=str(port_request_id),
            tenant_id=str(tenant_id),
        )
        return port_request

    async def complete_port(
        self,
        tenant_id: uuid.UUID,
        port_request_id: uuid.UUID,
        changed_by: uuid.UUID | None = None,
    ) -> PortRequest:
        """Mark a port as completed and activate the DIDs in the system."""
        port_request = await self.get_port_request(tenant_id, port_request_id)
        if not port_request:
            raise ValueError("Port request not found")

        if port_request.status != PortRequestStatus.IN_PROGRESS:
            raise ValueError(
                f"Can only complete ports that are 'in_progress', current: '{port_request.status}'"
            )

        # Activate DIDs — create DID records for each ported number
        from new_phone.models.did import DID, DIDStatus

        for number in port_request.numbers:
            # Check if DID already exists
            existing = await self.db.execute(
                select(DID).where(DID.number == number)
            )
            if existing.scalar_one_or_none():
                logger.warning(
                    "port_complete_did_exists",
                    number=number,
                    port_request_id=str(port_request_id),
                )
                continue

            did = DID(
                tenant_id=tenant_id,
                number=number,
                provider=port_request.provider,
                status=DIDStatus.ACTIVE,
                is_active=True,
            )
            self.db.add(did)
            logger.info(
                "port_complete_did_created",
                number=number,
                port_request_id=str(port_request_id),
            )

        port_request.actual_port_date = datetime.now(UTC).date()
        await self._transition_status(
            port_request, PortRequestStatus.COMPLETED, changed_by, "Port completed, DIDs activated"
        )

        await self.db.commit()
        await self.db.refresh(port_request)

        logger.info(
            "port_request_completed",
            port_request_id=str(port_request_id),
            numbers=port_request.numbers,
        )
        return port_request

    async def _transition_status(
        self,
        port_request: PortRequest,
        new_status: str,
        changed_by: uuid.UUID | None,
        notes: str | None,
    ) -> None:
        """Validate and execute a status transition."""
        current = port_request.status
        valid = VALID_TRANSITIONS.get(current, set())

        if new_status not in valid:
            raise ValueError(
                f"Invalid status transition from '{current}' to '{new_status}'. "
                f"Valid transitions: {sorted(valid) if valid else 'none (terminal state)'}"
            )

        history = PortRequestHistory(
            port_request_id=port_request.id,
            previous_status=current,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        self.db.add(history)
        port_request.status = new_status

        logger.info(
            "port_request_status_changed",
            port_request_id=str(port_request.id),
            from_status=current,
            to_status=new_status,
        )
