import json
import random
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from new_phone.db.rls import set_tenant_context
from new_phone.events.publisher import get_publisher
from new_phone.models.did import DID
from new_phone.models.queue import AgentStatus, Queue, QueueMember
from new_phone.models.sms import (
    Conversation,
    ConversationNote,
    ConversationState,
    Message,
    MessageDirection,
    MessageStatus,
    OptOutReason,
    SMSOptOut,
)
from new_phone.sms.factory import get_tenant_default_provider

logger = structlog.get_logger()


async def _publish_event(tenant_id: uuid.UUID, event_type: str, payload: dict) -> None:
    """Fire-and-forget event publish — never breaks the SMS flow."""
    try:
        publisher = get_publisher()
        await publisher.publish(tenant_id, event_type, payload)
    except Exception as e:
        logger.warning("event_publish_failed", event=event_type, error=str(e))

STOP_KEYWORDS = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
START_KEYWORDS = {"start", "unstop", "subscribe"}
HELP_KEYWORDS = {"help", "info"}


class SMSService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Conversations ────────────────────────────────────────────

    async def list_conversations(
        self,
        tenant_id: uuid.UUID,
        state_filter: str | None = None,
        queue_id: uuid.UUID | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[Conversation], int]:
        await set_tenant_context(self.db, tenant_id)

        query = (
            select(Conversation)
            .where(Conversation.tenant_id == tenant_id, Conversation.is_active.is_(True))
            .options(
                selectinload(Conversation.did),
                selectinload(Conversation.assigned_to_user),
                selectinload(Conversation.queue),
            )
        )
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.tenant_id == tenant_id, Conversation.is_active.is_(True)
        )

        if state_filter:
            query = query.where(Conversation.state == state_filter)
            count_query = count_query.where(Conversation.state == state_filter)

        if queue_id:
            query = query.where(Conversation.queue_id == queue_id)
            count_query = count_query.where(Conversation.queue_id == queue_id)

        query = query.order_by(Conversation.last_message_at.desc().nullslast())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await self.db.execute(query)
        conversations = list(result.unique().scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return conversations, total

    async def get_conversation(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation | None:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.tenant_id == tenant_id)
            .options(
                selectinload(Conversation.did),
                selectinload(Conversation.assigned_to_user),
                selectinload(Conversation.queue),
                selectinload(Conversation.messages),
                selectinload(Conversation.notes),
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_or_create_conversation(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID, remote_number: str
    ) -> Conversation:
        """Find existing conversation or create a new one."""
        result = await self.db.execute(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.did_id == did_id,
                Conversation.remote_number == remote_number,
            )
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            # Re-open if archived/resolved
            if conversation.state in (ConversationState.RESOLVED, ConversationState.ARCHIVED):
                conversation.state = ConversationState.OPEN
                conversation.resolved_at = None
            return conversation

        conversation = Conversation(
            tenant_id=tenant_id,
            did_id=did_id,
            remote_number=remote_number,
            state=ConversationState.OPEN,
        )
        self.db.add(conversation)
        await self.db.flush()
        await _publish_event(tenant_id, "conversation.created", {"conversation_id": str(conversation.id)})
        return conversation

    async def update_conversation(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        state: str | None = None,
        assigned_to_user_id: uuid.UUID | None = None,
        queue_id: uuid.UUID | None = ...,  # type: ignore[assignment]  # sentinel
    ) -> Conversation:
        await set_tenant_context(self.db, tenant_id)
        conversation = await self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        if state is not None:
            conversation.state = state
            if state == ConversationState.RESOLVED:
                conversation.resolved_at = datetime.now(UTC)

        if assigned_to_user_id is not None:
            conversation.assigned_to_user_id = assigned_to_user_id

        if queue_id is not ...:
            conversation.queue_id = queue_id

        await self.db.commit()
        await self.db.refresh(conversation)
        await _publish_event(tenant_id, "conversation.updated", {
            "conversation_id": str(conversation_id),
            "state": conversation.state,
        })
        return conversation

    # ── Messages ─────────────────────────────────────────────────

    async def send_message(
        self,
        tenant_id: uuid.UUID,
        conversation_id: uuid.UUID,
        body: str,
        sent_by_user_id: uuid.UUID,
        media_urls: list[str] | None = None,
    ) -> Message:
        await set_tenant_context(self.db, tenant_id)

        conversation = await self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        # Check opt-out
        is_opted_out = await self.check_opt_out(tenant_id, conversation.did_id, conversation.remote_number)
        if is_opted_out:
            raise ValueError(f"Cannot send SMS to {conversation.remote_number} — recipient has opted out")

        # Get provider
        config, provider = await get_tenant_default_provider(self.db, tenant_id)

        # Get DID number
        did_number = conversation.did.number if conversation.did else None
        if not did_number:
            raise ValueError("Conversation DID not found")

        media_urls_json = json.dumps(media_urls) if media_urls else None

        # Send via provider
        try:
            result = await provider.send_message(
                did_number, conversation.remote_number, body, media_urls=media_urls
            )
        except Exception as e:
            logger.error("sms_send_failed", error=str(e), conversation_id=str(conversation_id))
            # Record failed message with retry scheduling
            message = Message(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                direction=MessageDirection.OUTBOUND,
                from_number=did_number,
                to_number=conversation.remote_number,
                body=body,
                media_urls=media_urls_json,
                status=MessageStatus.FAILED,
                provider=config.provider_type,
                sent_by_user_id=sent_by_user_id,
                error_message=str(e),
                segments=1,
                retry_count=0,
                next_retry_at=datetime.now(UTC) + timedelta(seconds=60),
                max_retries=3,
            )
            self.db.add(message)
            conversation.last_message_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(message)
            raise

        # Record successful message
        message = Message(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            direction=MessageDirection.OUTBOUND,
            from_number=did_number,
            to_number=conversation.remote_number,
            body=body,
            media_urls=media_urls_json,
            status=result.status,
            provider=config.provider_type,
            provider_message_id=result.provider_message_id,
            sent_by_user_id=sent_by_user_id,
            segments=result.segments,
        )
        self.db.add(message)

        # Update conversation timestamps
        now = datetime.now(UTC)
        conversation.last_message_at = now
        if not conversation.first_response_at:
            conversation.first_response_at = now

        # Move to waiting state after agent reply
        if conversation.state == ConversationState.OPEN:
            conversation.state = ConversationState.WAITING

        await self.db.commit()
        await self.db.refresh(message)
        await _publish_event(tenant_id, "sms.sent", {
            "conversation_id": str(conversation_id),
            "message_id": str(message.id),
        })
        return message

    async def receive_message(
        self,
        did_number: str,
        from_number: str,
        body: str,
        media_urls: list[str] | None,
        provider: str,
        provider_message_id: str,
    ) -> Message:
        """Process an inbound SMS. Called from webhook handler with admin session."""
        # Find DID
        result = await self.db.execute(
            select(DID).where(DID.number == did_number, DID.sms_enabled.is_(True))
        )
        did = result.scalar_one_or_none()
        if not did:
            raise ValueError(f"DID {did_number} not found or SMS not enabled")

        tenant_id = did.tenant_id

        # Check for opt-out/in keywords
        keyword = body.strip().lower()
        if keyword in STOP_KEYWORDS or keyword in START_KEYWORDS or keyword in HELP_KEYWORDS:
            await self.process_opt_out_keyword(tenant_id, did.id, from_number, keyword, provider, did_number)

        # Check if sender is opted out (after processing keyword — STOP takes effect immediately)
        if keyword in STOP_KEYWORDS:
            logger.info("sms_inbound_from_opted_out", from_number=from_number, did=did_number)
            # Still record the STOP message in the conversation
            conversation = await self.get_or_create_conversation(tenant_id, did.id, from_number)
            message = Message(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                direction=MessageDirection.INBOUND,
                from_number=from_number,
                to_number=did_number,
                body=body,
                media_urls=json.dumps(media_urls) if media_urls else None,
                status=MessageStatus.RECEIVED,
                provider=provider,
                provider_message_id=provider_message_id,
            )
            self.db.add(message)
            conversation.last_message_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(message)
            return message

        # Check if already opted out
        is_opted_out = await self.check_opt_out(tenant_id, did.id, from_number)
        if is_opted_out:
            logger.info("sms_inbound_dropped_opted_out", from_number=from_number, did=did_number)
            # Silently drop — do not create message record
            raise ValueError("Sender is opted out")

        # Get or create conversation
        conversation = await self.get_or_create_conversation(tenant_id, did.id, from_number)

        # Queue routing: if DID has a queue and conversation has no queue yet, assign it
        is_new_to_queue = False
        if did.sms_queue_id and not conversation.queue_id:
            conversation.queue_id = did.sms_queue_id
            is_new_to_queue = True

        # Create message
        message = Message(
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            direction=MessageDirection.INBOUND,
            from_number=from_number,
            to_number=did_number,
            body=body,
            media_urls=json.dumps(media_urls) if media_urls else None,
            status=MessageStatus.RECEIVED,
            provider=provider,
            provider_message_id=provider_message_id,
        )
        self.db.add(message)

        conversation.last_message_at = datetime.now(UTC)

        # If conversation was waiting (agent replied, waiting for customer), move back to open
        if conversation.state == ConversationState.WAITING:
            conversation.state = ConversationState.OPEN

        # Auto-assign to agent if conversation is newly routed to a queue and unassigned
        if is_new_to_queue and not conversation.assigned_to_user_id:
            assigned_user_id = await self._auto_assign_agent(tenant_id, did.sms_queue_id)
            if assigned_user_id:
                conversation.assigned_to_user_id = assigned_user_id

        await self.db.commit()
        await self.db.refresh(message)
        await _publish_event(tenant_id, "sms.received", {
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "from_number": from_number,
            "body_preview": body[:100] if body else "",
        })

        # Publish assignment event if we auto-assigned
        if is_new_to_queue:
            await _publish_event(tenant_id, "conversation.assigned", {
                "conversation_id": str(conversation.id),
                "assigned_to_user_id": str(conversation.assigned_to_user_id) if conversation.assigned_to_user_id else None,
                "queue_id": str(conversation.queue_id) if conversation.queue_id else None,
            })

        return message

    async def update_message_status(
        self, provider_message_id: str, status: str, error_message: str | None = None
    ) -> Message | None:
        """Update message delivery status from provider callback. Admin session."""
        result = await self.db.execute(
            select(Message).where(Message.provider_message_id == provider_message_id)
        )
        message = result.scalar_one_or_none()
        if not message:
            logger.warning("sms_status_update_message_not_found", provider_message_id=provider_message_id)
            return None

        message.status = status
        if error_message:
            message.error_message = error_message

        await self.db.commit()
        await self.db.refresh(message)
        await _publish_event(message.tenant_id, "sms.status_updated", {
            "conversation_id": str(message.conversation_id),
            "message_id": str(message.id),
            "status": status,
        })
        return message

    async def list_messages(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[Message]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.tenant_id == tenant_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Assignment ─────────────────────────────────────────────

    async def _auto_assign_agent(
        self, tenant_id: uuid.UUID, queue_id: uuid.UUID
    ) -> uuid.UUID | None:
        """Pick the best available agent from a queue for SMS assignment."""
        # Load queue with members
        result = await self.db.execute(
            select(Queue)
            .where(Queue.id == queue_id, Queue.enabled.is_(True))
            .options(selectinload(Queue.members).selectinload(QueueMember.extension))
        )
        queue = result.unique().scalar_one_or_none()
        if not queue or not queue.members:
            return None

        # Build candidate list: members with available agents that have a user
        candidates: list[tuple[QueueMember, uuid.UUID]] = []
        for member in queue.members:
            ext = member.extension
            if (
                ext
                and ext.is_active
                and ext.user_id
                and ext.agent_status == AgentStatus.AVAILABLE
            ):
                candidates.append((member, ext.user_id))

        if not candidates:
            return None

        # Apply tier rules: only consider lowest level with available agents
        if queue.tier_rules_apply:
            min_level = min(m.level for m, _ in candidates)
            candidates = [(m, uid) for m, uid in candidates if m.level == min_level]

        if not candidates:
            return None

        # Count open SMS conversations per candidate
        user_ids = [uid for _, uid in candidates]
        open_counts: dict[uuid.UUID, int] = {}
        for uid in user_ids:
            count_result = await self.db.execute(
                select(func.count())
                .select_from(Conversation)
                .where(
                    Conversation.tenant_id == tenant_id,
                    Conversation.assigned_to_user_id == uid,
                    Conversation.state.in_([ConversationState.OPEN, ConversationState.WAITING]),
                    Conversation.is_active.is_(True),
                )
            )
            open_counts[uid] = count_result.scalar() or 0

        strategy = queue.strategy

        if strategy in ("longest-idle-agent", "ring-all", "agent-with-fewest-calls", "agent-with-least-talk-time"):
            # For SMS: pick agent with fewest open conversations
            candidates.sort(key=lambda c: open_counts.get(c[1], 0))
            return candidates[0][1]

        elif strategy in ("top-down", "sequentially-by-agent-order", "ring-progressively"):
            # First available by level+position order (already sorted)
            return candidates[0][1]

        elif strategy == "round-robin":
            # Rotate: pick agent with fewest open conversations (approximation)
            candidates.sort(key=lambda c: (open_counts.get(c[1], 0), c[0].position))
            return candidates[0][1]

        elif strategy == "random":
            return random.choice(candidates)[1]

        else:
            # Fallback: fewest open conversations
            candidates.sort(key=lambda c: open_counts.get(c[1], 0))
            return candidates[0][1]

    async def claim_conversation(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation:
        """Agent claims an unassigned conversation."""
        await set_tenant_context(self.db, tenant_id)
        conversation = await self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        conversation.assigned_to_user_id = user_id
        await self.db.commit()
        await self.db.refresh(conversation)

        await _publish_event(tenant_id, "conversation.assigned", {
            "conversation_id": str(conversation_id),
            "assigned_to_user_id": str(user_id),
            "queue_id": str(conversation.queue_id) if conversation.queue_id else None,
        })
        return conversation

    async def release_conversation(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, user_id: uuid.UUID, is_msp: bool = False
    ) -> Conversation:
        """Agent releases a conversation back to the shared inbox."""
        await set_tenant_context(self.db, tenant_id)
        conversation = await self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        if not is_msp and conversation.assigned_to_user_id != user_id:
            raise ValueError("You can only release conversations assigned to you")

        conversation.assigned_to_user_id = None
        await self.db.commit()
        await self.db.refresh(conversation)

        await _publish_event(tenant_id, "conversation.assigned", {
            "conversation_id": str(conversation_id),
            "assigned_to_user_id": None,
            "queue_id": str(conversation.queue_id) if conversation.queue_id else None,
        })
        return conversation

    async def reassign_conversation(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, new_user_id: uuid.UUID
    ) -> Conversation:
        """Supervisor reassigns a conversation to a different agent."""
        await set_tenant_context(self.db, tenant_id)
        conversation = await self.get_conversation(tenant_id, conversation_id)
        if not conversation:
            raise ValueError("Conversation not found")

        conversation.assigned_to_user_id = new_user_id
        await self.db.commit()
        await self.db.refresh(conversation)

        await _publish_event(tenant_id, "conversation.assigned", {
            "conversation_id": str(conversation_id),
            "assigned_to_user_id": str(new_user_id),
            "queue_id": str(conversation.queue_id) if conversation.queue_id else None,
        })
        return conversation

    # ── Notes ────────────────────────────────────────────────────

    async def create_note(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID, user_id: uuid.UUID, body: str
    ) -> ConversationNote:
        await set_tenant_context(self.db, tenant_id)
        note = ConversationNote(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            body=body,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return note

    async def list_notes(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> list[ConversationNote]:
        await set_tenant_context(self.db, tenant_id)
        result = await self.db.execute(
            select(ConversationNote)
            .where(
                ConversationNote.conversation_id == conversation_id,
                ConversationNote.tenant_id == tenant_id,
            )
            .order_by(ConversationNote.created_at.asc())
        )
        return list(result.scalars().all())

    # ── Opt-out ──────────────────────────────────────────────────

    async def check_opt_out(
        self, tenant_id: uuid.UUID, did_id: uuid.UUID, phone_number: str
    ) -> bool:
        result = await self.db.execute(
            select(SMSOptOut).where(
                SMSOptOut.tenant_id == tenant_id,
                SMSOptOut.did_id == did_id,
                SMSOptOut.phone_number == phone_number,
                SMSOptOut.is_opted_out.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    async def process_opt_out_keyword(
        self,
        tenant_id: uuid.UUID,
        did_id: uuid.UUID,
        phone_number: str,
        keyword: str,
        provider: str,
        did_number: str,
    ) -> None:
        """Handle STOP/START/HELP keywords with auto-reply."""
        from new_phone.sms.factory import get_tenant_default_provider

        if keyword in STOP_KEYWORDS:
            # Create or update opt-out
            result = await self.db.execute(
                select(SMSOptOut).where(
                    SMSOptOut.tenant_id == tenant_id,
                    SMSOptOut.did_id == did_id,
                    SMSOptOut.phone_number == phone_number,
                )
            )
            opt_out = result.scalar_one_or_none()
            if opt_out:
                opt_out.is_opted_out = True
                opt_out.opted_out_at = datetime.now(UTC)
                opt_out.opted_in_at = None
                opt_out.reason = OptOutReason.KEYWORD_STOP
            else:
                opt_out = SMSOptOut(
                    tenant_id=tenant_id,
                    did_id=did_id,
                    phone_number=phone_number,
                    reason=OptOutReason.KEYWORD_STOP,
                    opted_out_at=datetime.now(UTC),
                    is_opted_out=True,
                )
                self.db.add(opt_out)

            await self.db.flush()

            # Send auto-reply
            try:
                _config, prov = await get_tenant_default_provider(self.db, tenant_id)
                await prov.send_message(
                    did_number, phone_number,
                    "You have been unsubscribed and will no longer receive messages. Reply START to re-subscribe."
                )
            except Exception as e:
                logger.warning("sms_opt_out_auto_reply_failed", error=str(e))

        elif keyword in START_KEYWORDS:
            # Clear opt-out
            result = await self.db.execute(
                select(SMSOptOut).where(
                    SMSOptOut.tenant_id == tenant_id,
                    SMSOptOut.did_id == did_id,
                    SMSOptOut.phone_number == phone_number,
                )
            )
            opt_out = result.scalar_one_or_none()
            if opt_out:
                opt_out.is_opted_out = False
                opt_out.opted_in_at = datetime.now(UTC)
                await self.db.flush()

            # Send auto-reply
            try:
                _config, prov = await get_tenant_default_provider(self.db, tenant_id)
                await prov.send_message(
                    did_number, phone_number,
                    "You have been re-subscribed and will now receive messages. Reply STOP to unsubscribe."
                )
            except Exception as e:
                logger.warning("sms_opt_in_auto_reply_failed", error=str(e))

        elif keyword in HELP_KEYWORDS:
            try:
                _config, prov = await get_tenant_default_provider(self.db, tenant_id)
                await prov.send_message(
                    did_number, phone_number,
                    "Reply STOP to unsubscribe from messages. Reply START to re-subscribe."
                )
            except Exception as e:
                logger.warning("sms_help_auto_reply_failed", error=str(e))
