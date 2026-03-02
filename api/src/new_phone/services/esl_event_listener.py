"""Persistent ESL event listener for FreeSWITCH.

Subscribes to CHANNEL_HANGUP_COMPLETE, RECORD_STOP, and CUSTOM vm::maintenance events.
Creates CDRs, recording metadata, and voicemail messages in real-time.
"""

import asyncio
import contextlib
import hashlib
import os
import uuid
from datetime import UTC, datetime
from urllib.parse import unquote

import structlog
from sqlalchemy import select

from new_phone.config import settings
from new_phone.db.engine import AdminSessionLocal
from new_phone.models.cdr import CallDetailRecord
from new_phone.models.extension import Extension
from new_phone.models.recording import Recording
from new_phone.models.tenant import Tenant
from new_phone.models.voicemail_box import VoicemailBox
from new_phone.models.voicemail_message import VoicemailMessage
from new_phone.services.storage_service import StorageService

logger = structlog.get_logger()

# FreeSWITCH hangup cause → CDR disposition mapping
HANGUP_CAUSE_MAP = {
    "NORMAL_CLEARING": "answered",
    "ORIGINATOR_CANCEL": "cancelled",
    "NO_ANSWER": "no_answer",
    "NO_USER_RESPONSE": "no_answer",
    "USER_BUSY": "busy",
    "CALL_REJECTED": "busy",
    "NORMAL_TEMPORARY_FAILURE": "failed",
    "UNALLOCATED_NUMBER": "failed",
    "NORMAL_UNSPECIFIED": "answered",
    "ATTENDED_TRANSFER": "answered",
    "BLIND_TRANSFER": "answered",
}


def _disposition_from_hangup(hangup_cause: str, billsec: int) -> str:
    mapped = HANGUP_CAUSE_MAP.get(hangup_cause, "failed")
    if mapped == "answered" and billsec == 0:
        return "no_answer"
    return mapped


def _epoch_to_datetime(epoch_str: str) -> datetime | None:
    if not epoch_str or epoch_str == "0":
        return None
    try:
        return datetime.fromtimestamp(int(epoch_str), tz=UTC)
    except (ValueError, OSError):
        return None


class ESLEventListener:
    def __init__(self, storage: StorageService | None = None, email=None):
        self.host = settings.freeswitch_host
        self.port = settings.freeswitch_esl_port
        self.password = settings.freeswitch_esl_password
        self.storage = storage
        self.email = email  # EmailService instance
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._running = False
        self._task: asyncio.Task | None = None
        self._tenant_cache: dict[str, uuid.UUID] = {}
        self._background_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("esl_listener_started")

    async def stop(self) -> None:
        self._running = False
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("esl_listener_stopped")

    async def _run_loop(self) -> None:
        backoff = 1
        while self._running:
            try:
                await self._connect()
                backoff = 1
                await self._event_loop()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("esl_listener_error", error=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _connect(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

        # Read auth/welcome banner
        await self._read_message()

        # Authenticate
        self._writer.write(f"auth {self.password}\n\n".encode())
        await self._writer.drain()
        auth_response = await self._read_message()
        if "Reply-Text: +OK" not in auth_response:
            raise ConnectionError(f"ESL auth failed: {auth_response}")

        # Subscribe to events (including CUSTOM vm::maintenance, callcenter::info, valet_parking::info)
        self._writer.write(
            b"event plain CHANNEL_HANGUP_COMPLETE RECORD_STOP CUSTOM vm::maintenance callcenter::info valet_parking::info\n\n"
        )
        await self._writer.drain()
        await self._read_message()

        logger.info("esl_listener_connected")

    async def _event_loop(self) -> None:
        while self._running and self._reader:
            msg = await self._read_message()
            if not msg:
                raise ConnectionError("ESL connection lost")

            headers = self._parse_headers(msg)
            content_length = int(headers.get("Content-Length", "0"))
            body = ""
            if content_length > 0:
                raw = await self._reader.readexactly(content_length)
                body = raw.decode("utf-8", errors="replace")

            event_name = headers.get("Event-Name", "")
            if event_name:
                event_headers = self._parse_headers(body) if body else headers
                # Merge in top-level headers for variables not in body
                for k, v in headers.items():
                    if k not in event_headers:
                        event_headers[k] = v

                try:
                    if event_name == "CHANNEL_HANGUP_COMPLETE":
                        await self._handle_hangup(event_headers)
                    elif event_name == "RECORD_STOP":
                        await self._handle_record_stop(event_headers)
                    elif event_name == "CUSTOM":
                        subclass = event_headers.get("Event-Subclass", "")
                        if subclass == "vm::maintenance":
                            await self._handle_voicemail(event_headers)
                        elif subclass == "callcenter::info":
                            await self._handle_callcenter_event(event_headers)
                        elif subclass == "valet_parking::info":
                            await self._handle_valet_parking_event(event_headers)
                except Exception as e:
                    logger.error("esl_event_handler_error", event=event_name, error=str(e))

    async def _read_message(self) -> str:
        lines = []
        while True:
            line = await self._reader.readline()
            if not line:
                return ""
            decoded = line.decode("utf-8", errors="replace").rstrip("\n")
            if decoded == "":
                break
            lines.append(decoded)
        return "\n".join(lines)

    def _parse_headers(self, text: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        for line in text.split("\n"):
            if ": " in line:
                key, _, value = line.partition(": ")
                headers[key.strip()] = unquote(value.strip())
        return headers

    async def _resolve_tenant(self, accountcode: str) -> uuid.UUID | None:
        if not accountcode:
            return None
        if accountcode in self._tenant_cache:
            return self._tenant_cache[accountcode]

        async with AdminSessionLocal() as session:
            result = await session.execute(select(Tenant.id).where(Tenant.slug == accountcode))
            tenant_id = result.scalar_one_or_none()
            if tenant_id:
                self._tenant_cache[accountcode] = tenant_id
            return tenant_id

    async def _handle_hangup(self, headers: dict[str, str]) -> None:
        call_id = headers.get("Unique-ID", headers.get("variable_uuid", ""))
        if not call_id:
            return

        accountcode = headers.get("variable_accountcode", "")
        tenant_id = await self._resolve_tenant(accountcode)
        if not tenant_id:
            logger.debug("esl_cdr_no_tenant", call_id=call_id, accountcode=accountcode)
            return

        hangup_cause = headers.get(
            "Hangup-Cause", headers.get("variable_hangup_cause", "NORMAL_CLEARING")
        )
        duration = int(headers.get("variable_duration", "0"))
        billsec = int(headers.get("variable_billsec", "0"))
        waitsec = int(headers.get("variable_waitsec", "0"))

        start_epoch = headers.get("variable_start_epoch", "0")
        answer_epoch = headers.get("variable_answer_epoch", "0")
        end_epoch = headers.get("variable_end_epoch", "0")

        start_time = _epoch_to_datetime(start_epoch)
        answer_time = _epoch_to_datetime(answer_epoch)
        end_time = _epoch_to_datetime(end_epoch)

        if not start_time or not end_time:
            now = datetime.now(UTC)
            end_time = end_time or now
            start_time = start_time or now

        direction = headers.get("variable_direction", headers.get("Call-Direction", "internal"))
        caller_number = headers.get(
            "Caller-Caller-ID-Number", headers.get("variable_caller_id_number", "")
        )
        caller_name = headers.get(
            "Caller-Caller-ID-Name", headers.get("variable_caller_id_name", "")
        )
        called_number = headers.get(
            "Caller-Destination-Number", headers.get("variable_destination_number", "")
        )

        disposition = _disposition_from_hangup(hangup_cause, billsec)

        async with AdminSessionLocal() as session:
            # Check for duplicate
            existing = await session.execute(
                select(CallDetailRecord.id).where(CallDetailRecord.call_id == call_id)
            )
            if existing.scalar_one_or_none():
                return

            cdr = CallDetailRecord(
                tenant_id=tenant_id,
                call_id=call_id,
                direction=direction,
                caller_number=caller_number,
                caller_name=caller_name,
                called_number=called_number,
                disposition=disposition,
                hangup_cause=hangup_cause,
                duration_seconds=duration,
                billable_seconds=billsec,
                ring_seconds=waitsec,
                start_time=start_time,
                answer_time=answer_time,
                end_time=end_time,
            )
            session.add(cdr)
            await session.commit()
            logger.info("cdr_created", call_id=call_id, disposition=disposition, duration=duration)

            # Fire-and-forget ConnectWise ticket creation
            task = asyncio.create_task(self._process_connectwise_ticket(tenant_id, cdr.id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            # Fire-and-forget CRM enrichment
            task = asyncio.create_task(self._process_crm_enrichment(tenant_id, cdr.id))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

            # Fire-and-forget AI engine cleanup for AI agent calls
            ai_context_id = headers.get("variable_ai_agent_context", "")
            if ai_context_id:
                task = asyncio.create_task(
                    self._notify_ai_engine_hangup(
                        call_id, str(tenant_id), ai_context_id, str(cdr.id)
                    )
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

            # Check for panic alert trigger
            panic_alert = headers.get("variable_panic_alert", "")
            if panic_alert == "true":
                task = asyncio.create_task(self._process_panic_alert(tenant_id, headers))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

            # Fire-and-forget camp-on target availability check
            task = asyncio.create_task(
                self._check_camp_on_target(tenant_id, called_number, accountcode)
            )
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _handle_record_stop(self, headers: dict[str, str]) -> None:
        call_id = headers.get("Unique-ID", headers.get("variable_uuid", ""))
        record_file = headers.get("Record-File-Path", headers.get("variable_record_file_path", ""))
        if not call_id or not record_file:
            return

        accountcode = headers.get("variable_accountcode", "")
        tenant_id = await self._resolve_tenant(accountcode)
        if not tenant_id:
            return

        record_seconds = int(headers.get("variable_record_seconds", "0"))
        object_name = f"{accountcode}/{call_id}.wav"

        # Upload to MinIO
        file_size = 0
        sha256 = None
        uploaded = False

        if os.path.exists(record_file) and self.storage:
            try:
                file_size = os.path.getsize(record_file)
                with open(record_file, "rb") as f:
                    sha256 = hashlib.sha256(f.read()).hexdigest()
                uploaded = self.storage.upload_file(object_name, record_file)
                if uploaded:
                    # Clean up local file
                    os.remove(record_file)
            except Exception as e:
                logger.error("recording_upload_error", call_id=call_id, error=str(e))

        async with AdminSessionLocal() as session:
            recording = Recording(
                tenant_id=tenant_id,
                call_id=call_id,
                storage_path=object_name if uploaded else None,
                storage_bucket=settings.minio_bucket if uploaded else None,
                file_size_bytes=file_size,
                duration_seconds=record_seconds,
                sha256_hash=sha256,
            )

            # Link to CDR if exists
            cdr_result = await session.execute(
                select(CallDetailRecord).where(CallDetailRecord.call_id == call_id)
            )
            cdr = cdr_result.scalar_one_or_none()
            if cdr:
                recording.cdr_id = cdr.id
                cdr.has_recording = True

            session.add(recording)
            await session.commit()
            logger.info("recording_created", call_id=call_id, uploaded=uploaded, size=file_size)

    async def _handle_voicemail(self, headers: dict[str, str]) -> None:
        """Handle vm::maintenance events from FreeSWITCH voicemail module."""
        vm_action = headers.get("VM-Action", "")
        vm_user = headers.get("VM-User", "")
        vm_domain = headers.get("VM-Domain", "")

        if not vm_user or not vm_domain:
            return

        if vm_action == "leave-message":
            await self._handle_vm_leave(headers, vm_user, vm_domain)
        elif vm_action == "delete-message":
            await self._handle_vm_status_change(headers, "deleted")
        elif vm_action == "save-message":
            await self._handle_vm_status_change(headers, "saved")
        elif vm_action == "read-message":
            await self._handle_vm_read(headers)

    async def _handle_vm_leave(self, headers: dict[str, str], vm_user: str, vm_domain: str) -> None:
        """Handle new voicemail message left."""
        # Resolve tenant from domain (strip .sip.local)
        slug = vm_domain.replace(".sip.local", "")
        tenant_id = await self._resolve_tenant(slug)
        if not tenant_id:
            logger.debug("vm_leave_no_tenant", user=vm_user, domain=vm_domain)
            return

        # Find voicemail box
        async with AdminSessionLocal() as session:
            result = await session.execute(
                select(VoicemailBox).where(
                    VoicemailBox.tenant_id == tenant_id,
                    VoicemailBox.mailbox_number == vm_user,
                    VoicemailBox.is_active.is_(True),
                )
            )
            vm_box = result.scalar_one_or_none()
            if not vm_box:
                logger.debug("vm_leave_no_box", user=vm_user, tenant_id=str(tenant_id))
                return

            caller_number = headers.get("VM-Caller-ID-Number", "")
            caller_name = headers.get("VM-Caller-ID-Name", "")
            duration = int(headers.get("VM-Message-Len", headers.get("VM-Duration", "0")))
            vm_file = headers.get("VM-File-Path", "")
            call_id = headers.get("VM-UUID", headers.get("Unique-ID", ""))

            # Upload audio to MinIO
            object_name = f"{slug}/voicemail/{vm_user}/{uuid.uuid4()}.wav"
            file_size = 0
            sha256 = None
            uploaded = False

            if vm_file and os.path.exists(vm_file) and self.storage:
                try:
                    file_size = os.path.getsize(vm_file)
                    with open(vm_file, "rb") as f:
                        file_data = f.read()
                        sha256 = hashlib.sha256(file_data).hexdigest()
                    uploaded = self.storage.upload_file(object_name, vm_file)
                except Exception as e:
                    logger.error("vm_upload_error", error=str(e))

            msg = VoicemailMessage(
                tenant_id=tenant_id,
                voicemail_box_id=vm_box.id,
                caller_number=caller_number,
                caller_name=caller_name,
                duration_seconds=duration,
                storage_path=object_name if uploaded else None,
                storage_bucket=settings.minio_bucket if uploaded else None,
                file_size_bytes=file_size,
                sha256_hash=sha256,
                call_id=call_id,
            )
            session.add(msg)
            await session.commit()
            logger.info(
                "voicemail_message_created", box=vm_user, caller=caller_number, duration=duration
            )

            # Send email notification
            if vm_box.email_notification and vm_box.notification_email and self.email:
                audio_data = None
                if vm_file and os.path.exists(vm_file):
                    try:
                        with open(vm_file, "rb") as f:
                            audio_data = f.read()
                    except OSError:
                        pass
                self.email.send_voicemail_notification(
                    to_email=vm_box.notification_email,
                    mailbox_number=vm_box.mailbox_number,
                    caller_number=caller_number,
                    caller_name=caller_name,
                    duration_seconds=duration,
                    audio_data=audio_data,
                )
                msg.email_sent = True
                await session.commit()

    async def _handle_vm_status_change(self, headers: dict[str, str], new_folder: str) -> None:
        """Handle voicemail message status changes (delete/save)."""
        call_id = headers.get("VM-UUID", headers.get("Unique-ID", ""))
        if not call_id:
            return

        async with AdminSessionLocal() as session:
            result = await session.execute(
                select(VoicemailMessage).where(VoicemailMessage.call_id == call_id)
            )
            msg = result.scalar_one_or_none()
            if msg:
                msg.folder = new_folder
                if new_folder == "deleted":
                    msg.is_active = False
                await session.commit()
                logger.info("voicemail_status_changed", call_id=call_id, folder=new_folder)

    async def _handle_vm_read(self, headers: dict[str, str]) -> None:
        """Handle voicemail message read event."""
        call_id = headers.get("VM-UUID", headers.get("Unique-ID", ""))
        if not call_id:
            return

        async with AdminSessionLocal() as session:
            result = await session.execute(
                select(VoicemailMessage).where(VoicemailMessage.call_id == call_id)
            )
            msg = result.scalar_one_or_none()
            if msg:
                msg.is_read = True
                msg.folder = "saved"
                await session.commit()
                logger.info("voicemail_read", call_id=call_id)

    async def _handle_callcenter_event(self, headers: dict[str, str]) -> None:
        """Handle callcenter::info events from FreeSWITCH mod_callcenter.

        Syncs agent status changes (from feature codes or FS commands) back to the DB.
        """
        cc_action = headers.get("CC-Action", "")
        if cc_action != "agent-status-change":
            return

        agent_name = headers.get("CC-Agent", "")
        new_status = headers.get("CC-Agent-Status", "")
        if not agent_name or not new_status:
            return

        # Agent name format: {ext_number}@{sip_domain}
        if "@" not in agent_name:
            return

        ext_number, domain = agent_name.split("@", 1)

        # Resolve tenant from domain
        slug = domain.replace(".sip.local", "")
        tenant_id = await self._resolve_tenant(slug)
        if not tenant_id:
            logger.debug("cc_event_no_tenant", agent=agent_name, domain=domain)
            return

        async with AdminSessionLocal() as session:
            result = await session.execute(
                select(Extension).where(
                    Extension.tenant_id == tenant_id,
                    Extension.extension_number == ext_number,
                    Extension.is_active.is_(True),
                )
            )
            ext = result.scalar_one_or_none()
            if ext:
                ext.agent_status = new_status
                await session.commit()
                logger.info(
                    "cc_agent_status_synced",
                    agent=agent_name,
                    status=new_status,
                )

    async def _handle_valet_parking_event(self, headers: dict[str, str]) -> None:
        """Handle valet_parking::info events from FreeSWITCH mod_valet_parking.

        Updates Redis slot state and publishes WebSocket events for the live parking panel.
        """
        import json

        lot_name = headers.get("Valet-Lot-Name", "")
        action = headers.get("Valet-Action", "")
        slot_id = headers.get("Valet-Extension", headers.get("Valet-Slot-ID", ""))

        if not lot_name or not slot_id:
            return

        # Lot name format: valet_parking@{sip_domain}
        if "@" not in lot_name:
            return

        _, domain = lot_name.split("@", 1)
        slug = domain.replace(".sip.local", "")
        tenant_id = await self._resolve_tenant(slug)
        if not tenant_id:
            logger.debug("valet_parking_no_tenant", lot=lot_name, domain=domain)
            return

        redis_key = f"parking_slot:{tenant_id}:{slot_id}"

        try:
            from new_phone.main import event_publisher, redis_client

            if not redis_client:
                return

            if action in ("hold", "bridge-incoming"):
                # Call parked — write slot state to Redis
                caller_number = headers.get("Caller-Caller-ID-Number", "")
                caller_name = headers.get("Caller-Caller-ID-Name", "")
                parked_by = headers.get("variable_effective_caller_id_number", "")
                slot_data = json.dumps(
                    {
                        "lot_name": lot_name,
                        "slot_number": int(slot_id),
                        "occupied": True,
                        "caller_id_number": caller_number,
                        "caller_id_name": caller_name,
                        "parked_at": datetime.now(UTC).isoformat(),
                        "parked_by": parked_by,
                    }
                )
                await redis_client.set(redis_key, slot_data, ex=600)
                logger.info("parking_slot_occupied", slot=slot_id, caller=caller_number)

                if event_publisher:
                    await event_publisher.publish(
                        tenant_id,
                        "parking.slot_occupied",
                        {
                            "slot_number": int(slot_id),
                            "caller_id_number": caller_number,
                            "caller_id_name": caller_name,
                            "parked_by": parked_by,
                        },
                    )

            elif action in ("exit", "bridge-outgoing"):
                # Call retrieved — delete slot state from Redis
                await redis_client.delete(redis_key)
                logger.info("parking_slot_cleared", slot=slot_id)

                if event_publisher:
                    await event_publisher.publish(
                        tenant_id,
                        "parking.slot_cleared",
                        {
                            "slot_number": int(slot_id),
                        },
                    )

        except Exception as e:
            logger.error("valet_parking_handler_error", error=str(e), slot=slot_id)

    async def _process_panic_alert(self, tenant_id: uuid.UUID, headers: dict[str, str]) -> None:
        """Fire-and-forget: trigger panic alert from desk phone feature code."""
        try:
            from new_phone.schemas.panic_alert import PanicAlertTriggerRequest
            from new_phone.services.panic_alert_service import PanicAlertService

            caller_number = headers.get(
                "Caller-Caller-ID-Number", headers.get("variable_caller_id_number", "")
            )

            async with AdminSessionLocal() as session:
                # Find the extension that triggered the panic
                ext_result = await session.execute(
                    select(Extension).where(
                        Extension.tenant_id == tenant_id,
                        Extension.extension_number == caller_number,
                    )
                )
                ext = ext_result.scalar_one_or_none()

                service = PanicAlertService(session)
                trigger_data = PanicAlertTriggerRequest(
                    alert_type="audible",
                    trigger_source="desk_phone",
                    extension_id=ext.id if ext else None,
                )
                await service.trigger_alert(tenant_id, None, trigger_data)

            logger.critical(
                "panic_alert_from_desk_phone", tenant_id=str(tenant_id), caller=caller_number
            )
        except Exception as e:
            logger.error("panic_alert_processing_error", error=str(e), tenant_id=str(tenant_id))

    async def _process_crm_enrichment(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> None:
        """Fire-and-forget: enrich CDR with CRM contact data. Never crashes the event listener."""
        try:
            from new_phone.main import redis_client
            from new_phone.services.crm_enrichment_service import CRMEnrichmentService

            async with AdminSessionLocal() as session:
                service = CRMEnrichmentService(session, redis=redis_client)
                await service.enrich_cdr(tenant_id, cdr_id)
        except Exception as e:
            logger.error("crm_enrichment_background_error", error=str(e), cdr_id=str(cdr_id))

    async def _process_connectwise_ticket(self, tenant_id: uuid.UUID, cdr_id: uuid.UUID) -> None:
        """Fire-and-forget: create ConnectWise ticket from CDR. Never crashes the event listener."""
        try:
            from new_phone.main import redis_client
            from new_phone.services.connectwise_service import ConnectWiseService

            async with AdminSessionLocal() as session:
                service = ConnectWiseService(session, redis=redis_client)
                await service.create_ticket_from_cdr(tenant_id, cdr_id)
        except Exception as e:
            logger.error("cw_ticket_background_error", error=str(e), cdr_id=str(cdr_id))

    async def _check_camp_on_target(
        self, tenant_id: uuid.UUID, called_number: str, accountcode: str
    ) -> None:
        """Check if the called extension has pending camp-on requests.

        Called as fire-and-forget after every hangup. If the target just became
        free (no active channels, not DND), trigger a callback for the oldest
        pending camp-on request.
        """
        if not called_number:
            return
        try:
            from new_phone.main import freeswitch_service, redis_client

            if not redis_client or not freeswitch_service:
                return

            from new_phone.services.camp_on_service import CampOnService

            service = CampOnService.__new__(CampOnService)
            service.db = None  # type: ignore[assignment]
            service.redis = redis_client

            pending_ids = await service.get_pending_for_target(tenant_id, called_number)
            if not pending_ids:
                return

            # Verify target has no active channels
            async with AdminSessionLocal() as session:
                ext_result = await session.execute(
                    select(Extension).where(
                        Extension.tenant_id == tenant_id,
                        Extension.extension_number == called_number,
                        Extension.is_active.is_(True),
                    )
                )
                target_ext = ext_result.scalar_one_or_none()
                if not target_ext:
                    return

                # Check DND
                if target_ext.dnd_enabled:
                    return

                # Check if target still has active channels
                active = await freeswitch_service.show_channels_for_user(target_ext.sip_username)
                if active:
                    return

                # Pick oldest pending request and trigger callback
                oldest_id = sorted(pending_ids)[0]
                await self._execute_camp_on_callback(tenant_id, uuid.UUID(oldest_id))

        except Exception as e:
            logger.error(
                "camp_on_target_check_error",
                error=str(e),
                tenant_id=str(tenant_id),
                called=called_number,
            )

    async def _execute_camp_on_callback(self, tenant_id: uuid.UUID, request_id: uuid.UUID) -> None:
        """Initiate a camp-on callback: ring the original caller, bridge to target."""
        try:
            from new_phone.main import freeswitch_service, redis_client

            if not freeswitch_service:
                return

            async with AdminSessionLocal() as session:
                from new_phone.services.camp_on_service import CampOnService

                service = CampOnService(session, redis=redis_client)
                request = await service.get_request(tenant_id, request_id)
                if not request or request.status != "pending":
                    return

                # Load config for retry delay
                config = await service.get_config(tenant_id)

                # Mark as callback_initiated
                initiated = await service.initiate_callback(request_id)
                if not initiated:
                    return

            # Originate: ring caller SIP user → bridge to target extension number
            domain = None
            async with AdminSessionLocal() as session:
                tenant_result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
                tenant = tenant_result.scalar_one_or_none()
                if tenant:
                    domain = tenant.sip_domain or f"{tenant.slug}.sip.local"

            if not domain:
                return

            result = await freeswitch_service.originate_call(
                sip_username=request.caller_sip_username,
                destination=request.target_extension_number,
                timeout=30,
            )

            if result and "+OK" in result:
                # Callback originated successfully — mark connected
                async with AdminSessionLocal() as session:
                    svc = CampOnService(session, redis=redis_client)
                    await svc.handle_callback_success(request_id)
                logger.info("camp_on_callback_success", request_id=str(request_id))
            else:
                await self._handle_camp_on_callback_failure(tenant_id, request_id, config)

        except Exception as e:
            logger.error(
                "camp_on_callback_error",
                error=str(e),
                request_id=str(request_id),
            )

    async def _handle_camp_on_callback_failure(
        self, tenant_id: uuid.UUID, request_id: uuid.UUID, config=None
    ) -> None:
        """Handle failed camp-on callback. Retry once after delay, then cancel."""
        try:
            from new_phone.main import redis_client

            async with AdminSessionLocal() as session:
                from new_phone.services.camp_on_service import CampOnService

                service = CampOnService(session, redis=redis_client)
                should_retry = await service.handle_callback_failure(request_id)

            if should_retry:
                retry_delay = 30
                if config:
                    retry_delay = config.callback_retry_delay_seconds
                await asyncio.sleep(retry_delay)
                await self._execute_camp_on_callback(tenant_id, request_id)
        except Exception as e:
            logger.error(
                "camp_on_failure_handler_error",
                error=str(e),
                request_id=str(request_id),
            )

    async def _notify_ai_engine_hangup(
        self, call_id: str, tenant_id: str, context_id: str, cdr_id: str
    ) -> None:
        """Fire-and-forget: notify AI engine that an AI-handled call ended.

        The AI engine will cleanup the session and persist the conversation log.
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{settings.ai_engine_url}/stop",
                    json={
                        "call_id": call_id,
                        "tenant_id": tenant_id,
                        "context_id": context_id,
                        "cdr_id": cdr_id,
                    },
                )
                if resp.status_code < 400:
                    logger.info("ai_engine_hangup_notified", call_id=call_id)
                else:
                    logger.warning(
                        "ai_engine_hangup_notify_failed",
                        call_id=call_id,
                        status=resp.status_code,
                    )
        except Exception as e:
            logger.error("ai_engine_hangup_notify_error", call_id=call_id, error=str(e))
