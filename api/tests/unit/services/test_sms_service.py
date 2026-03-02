"""Tests for new_phone.services.sms_service — SMS conversations, messages, opt-out."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from new_phone.models.sms import ConversationState, MessageDirection, MessageStatus
from new_phone.services.sms_service import SMSService
from tests.unit.conftest import TENANT_ACME_ID, make_scalar_result


def _make_conversation(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        did_id=uuid.uuid4(),
        remote_number="+15559998888",
        state=ConversationState.OPEN,
        assigned_to_user_id=None,
        queue_id=None,
        is_active=True,
        first_response_at=None,
        last_message_at=None,
        resolved_at=None,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    # give the `did` relationship a number
    did_mock = MagicMock()
    did_mock.number = "+15551112222"
    obj.did = overrides.get("did", did_mock)
    return obj


def _make_message(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        direction=MessageDirection.OUTBOUND,
        from_number="+15551112222",
        to_number="+15559998888",
        body="Hello",
        status=MessageStatus.SENT,
        provider="clearlyip",
        provider_message_id="MSG_1",
        sent_by_user_id=uuid.uuid4(),
        error_message=None,
        segments=1,
        media_urls=None,
        retry_count=0,
        next_retry_at=None,
        max_retries=3,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_did_obj(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT_ACME_ID,
        number="+15551112222",
        sms_enabled=True,
        sms_queue_id=None,
    )
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ── list_conversations ───────────────────────────────────────────────────


class TestListConversations:
    async def test_returns_conversations_and_count(self, mock_db):
        conv = _make_conversation()
        result_mock = MagicMock()
        unique_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [conv]
        unique_mock.scalars.return_value = scalars_mock
        result_mock.unique.return_value = unique_mock

        count_mock = MagicMock()
        count_mock.scalar.return_value = 1

        mock_db.execute.side_effect = [result_mock, count_mock]

        service = SMSService(mock_db)
        convs, total = await service.list_conversations(TENANT_ACME_ID)
        assert len(convs) == 1
        assert total == 1


# ── get_conversation ─────────────────────────────────────────────────────


class TestGetConversation:
    async def test_found(self, mock_db):
        conv = _make_conversation()
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        result = await service.get_conversation(TENANT_ACME_ID, conv.id)
        assert result is conv

    async def test_not_found(self, mock_db):
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = None
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        result = await service.get_conversation(TENANT_ACME_ID, uuid.uuid4())
        assert result is None


# ── get_or_create_conversation ───────────────────────────────────────────


class TestGetOrCreateConversation:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_existing_returns_it(self, mock_pub, mock_db):
        conv = _make_conversation(state=ConversationState.OPEN)
        mock_db.execute.return_value = make_scalar_result(conv)

        service = SMSService(mock_db)
        result = await service.get_or_create_conversation(
            TENANT_ACME_ID, conv.did_id, "+15559998888"
        )
        assert result is conv
        mock_db.add.assert_not_called()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_creates_new_when_none(self, mock_pub, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)

        service = SMSService(mock_db)
        await service.get_or_create_conversation(
            TENANT_ACME_ID, uuid.uuid4(), "+15559998888"
        )
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_reopens_resolved(self, mock_pub, mock_db):
        conv = _make_conversation(state=ConversationState.RESOLVED, resolved_at=datetime.now(UTC))
        mock_db.execute.return_value = make_scalar_result(conv)

        service = SMSService(mock_db)
        await service.get_or_create_conversation(
            TENANT_ACME_ID, conv.did_id, "+15559998888"
        )
        assert conv.state == ConversationState.OPEN
        assert conv.resolved_at is None


# ── send_message ─────────────────────────────────────────────────────────


class TestSendMessage:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    @patch("new_phone.services.sms_service.get_tenant_default_provider")
    async def test_success(self, mock_get_provider, mock_pub, mock_db):
        conv = _make_conversation()
        # get_conversation uses unique()
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock

        # check_opt_out returns no opt-out
        opt_out_result = make_scalar_result(None)

        mock_db.execute.side_effect = [result_mock, opt_out_result]

        mock_config = MagicMock()
        mock_config.provider_type = "clearlyip"
        mock_provider = AsyncMock()
        send_result = MagicMock()
        send_result.status = MessageStatus.SENT
        send_result.provider_message_id = "MSG_1"
        send_result.segments = 1
        mock_provider.send_message.return_value = send_result
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = SMSService(mock_db)
        user_id = uuid.uuid4()
        await service.send_message(TENANT_ACME_ID, conv.id, "Hello!", user_id)
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_opted_out_raises(self, mock_pub, mock_db):
        conv = _make_conversation()
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock

        # opt-out check returns a record
        opt_out_mock = MagicMock()
        opt_out_result = make_scalar_result(opt_out_mock)

        mock_db.execute.side_effect = [result_mock, opt_out_result]

        service = SMSService(mock_db)
        with pytest.raises(ValueError, match="opted out"):
            await service.send_message(TENANT_ACME_ID, conv.id, "Hi", uuid.uuid4())

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    @patch("new_phone.services.sms_service.get_tenant_default_provider")
    async def test_provider_error_records_failed_message(self, mock_get_provider, mock_pub, mock_db):
        conv = _make_conversation()
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock

        opt_out_result = make_scalar_result(None)
        mock_db.execute.side_effect = [result_mock, opt_out_result]

        mock_config = MagicMock()
        mock_config.provider_type = "clearlyip"
        mock_provider = AsyncMock()
        mock_provider.send_message.side_effect = Exception("Provider down")
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = SMSService(mock_db)
        with pytest.raises(Exception, match="Provider down"):
            await service.send_message(TENANT_ACME_ID, conv.id, "Hello", uuid.uuid4())
        # Failed message should still be recorded
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()


# ── receive_message ──────────────────────────────────────────────────────


class TestReceiveMessage:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_normal_inbound(self, mock_pub, mock_db):
        did = _make_did_obj()
        conv = _make_conversation(did=MagicMock(number="+15551112222"))

        # 1. find DID
        # 2. check opt-out
        # 3. get_or_create_conversation
        mock_db.execute.side_effect = [
            make_scalar_result(did),  # find DID
            make_scalar_result(None),  # opt-out check
            make_scalar_result(conv),  # existing conversation
        ]

        service = SMSService(mock_db)
        await service.receive_message(
            "+15551112222", "+15559998888", "Hello!", None, "clearlyip", "PMSG_1"
        )
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    @patch("new_phone.sms.factory.get_tenant_default_provider")
    async def test_stop_keyword(self, mock_get_provider, mock_pub, mock_db):
        did = _make_did_obj()
        conv = _make_conversation()

        # STOP flow: find DID, opt-out check in process_opt_out_keyword,
        # get_or_create_conversation
        mock_db.execute.side_effect = [
            make_scalar_result(did),      # find DID
            make_scalar_result(None),      # process_opt_out_keyword: existing opt-out check
            make_scalar_result(conv),      # get_or_create_conversation
        ]
        mock_db.flush = AsyncMock()

        mock_config = MagicMock()
        mock_provider = AsyncMock()
        mock_get_provider.return_value = (mock_config, mock_provider)

        service = SMSService(mock_db)
        await service.receive_message(
            "+15551112222", "+15559998888", "STOP", None, "clearlyip", "PMSG_2"
        )
        mock_db.add.assert_called()
        mock_db.commit.assert_awaited()

    async def test_unknown_did_raises(self, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SMSService(mock_db)
        with pytest.raises(ValueError, match=r"DID.*not found"):
            await service.receive_message(
                "+15550000000", "+15559998888", "hi", None, "clearlyip", "X"
            )

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_opted_out_sender_raises(self, mock_pub, mock_db):
        did = _make_did_obj()
        # Simulate: not a keyword, already opted out
        mock_db.execute.side_effect = [
            make_scalar_result(did),
            make_scalar_result(MagicMock()),  # opt-out exists
        ]

        service = SMSService(mock_db)
        with pytest.raises(ValueError, match="opted out"):
            await service.receive_message(
                "+15551112222", "+15559998888", "hello", None, "clearlyip", "X"
            )


# ── update_message_status ────────────────────────────────────────────────


class TestUpdateMessageStatus:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_success(self, mock_pub, mock_db):
        msg = _make_message()
        mock_db.execute.return_value = make_scalar_result(msg)

        service = SMSService(mock_db)
        await service.update_message_status("MSG_1", "delivered")
        assert msg.status == "delivered"
        mock_db.commit.assert_awaited()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_message_not_found_returns_none(self, mock_pub, mock_db):
        mock_db.execute.return_value = make_scalar_result(None)
        service = SMSService(mock_db)
        result = await service.update_message_status("NONEXIST", "delivered")
        assert result is None


# ── claim_conversation ───────────────────────────────────────────────────


class TestClaimConversation:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_success(self, mock_pub, mock_db):
        conv = _make_conversation(assigned_to_user_id=None)
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        user_id = uuid.uuid4()
        service = SMSService(mock_db)
        await service.claim_conversation(TENANT_ACME_ID, conv.id, user_id)
        assert conv.assigned_to_user_id == user_id
        mock_db.commit.assert_awaited()

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_not_found_raises(self, mock_pub, mock_db):
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = None
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        with pytest.raises(ValueError, match="Conversation not found"):
            await service.claim_conversation(TENANT_ACME_ID, uuid.uuid4(), uuid.uuid4())


# ── release_conversation ─────────────────────────────────────────────────


class TestReleaseConversation:
    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_success(self, mock_pub, mock_db):
        user_id = uuid.uuid4()
        conv = _make_conversation(assigned_to_user_id=user_id)
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        await service.release_conversation(TENANT_ACME_ID, conv.id, user_id)
        assert conv.assigned_to_user_id is None

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_wrong_user_raises(self, mock_pub, mock_db):
        conv = _make_conversation(assigned_to_user_id=uuid.uuid4())
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        with pytest.raises(ValueError, match="only release"):
            await service.release_conversation(
                TENANT_ACME_ID, conv.id, uuid.uuid4()  # different user
            )

    @patch("new_phone.services.sms_service._publish_event", new_callable=AsyncMock)
    async def test_msp_can_release_any(self, mock_pub, mock_db):
        conv = _make_conversation(assigned_to_user_id=uuid.uuid4())
        result_mock = MagicMock()
        unique_mock = MagicMock()
        unique_mock.scalar_one_or_none.return_value = conv
        result_mock.unique.return_value = unique_mock
        mock_db.execute.return_value = result_mock

        service = SMSService(mock_db)
        await service.release_conversation(
            TENANT_ACME_ID, conv.id, uuid.uuid4(), is_msp=True
        )
        assert conv.assigned_to_user_id is None
