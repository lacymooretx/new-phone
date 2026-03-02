import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can detect them
from new_phone.config import settings
from new_phone.db.base import Base
from new_phone.models.ai_agent_context import AIAgentContext  # noqa: F401
from new_phone.models.ai_agent_conversation import AIAgentConversation  # noqa: F401
from new_phone.models.ai_agent_provider_config import AIAgentProviderConfig  # noqa: F401
from new_phone.models.ai_agent_tool_definition import AIAgentToolDefinition  # noqa: F401
from new_phone.models.audio_prompt import AudioPrompt  # noqa: F401
from new_phone.models.audit_log import AuditLog  # noqa: F401
from new_phone.models.boss_admin import BossAdminRelationship  # noqa: F401
from new_phone.models.caller_id_rule import CallerIdRule  # noqa: F401
from new_phone.models.cdr import CallDetailRecord  # noqa: F401
from new_phone.models.compliance_monitoring import (  # noqa: F401
    ComplianceEvaluation,
    ComplianceRule,
    ComplianceRuleResult,
)
from new_phone.models.conference_bridge import ConferenceBridge  # noqa: F401
from new_phone.models.cw_company_mapping import CWCompanyMapping  # noqa: F401
from new_phone.models.cw_config import CWConfig  # noqa: F401
from new_phone.models.cw_ticket_log import CWTicketLog  # noqa: F401
from new_phone.models.device import Device, DeviceKey  # noqa: F401
from new_phone.models.did import DID  # noqa: F401
from new_phone.models.dnc import (  # noqa: F401
    ComplianceAuditLog,
    ComplianceSettings,
    ConsentRecord,
    DNCEntry,
    DNCList,
)
from new_phone.models.extension import Extension  # noqa: F401
from new_phone.models.follow_me import FollowMe, FollowMeDestination  # noqa: F401
from new_phone.models.holiday_calendar import HolidayCalendar, HolidayEntry  # noqa: F401
from new_phone.models.inbound_route import InboundRoute  # noqa: F401
from new_phone.models.ivr_menu import IVRMenu, IVRMenuOption  # noqa: F401
from new_phone.models.outbound_route import OutboundRoute, OutboundRouteTrunk  # noqa: F401
from new_phone.models.page_group import PageGroup, PageGroupMember  # noqa: F401
from new_phone.models.phone_model import PhoneModel  # noqa: F401
from new_phone.models.queue import Queue, QueueMember  # noqa: F401
from new_phone.models.recording import Recording  # noqa: F401
from new_phone.models.ring_group import RingGroup, RingGroupMember  # noqa: F401
from new_phone.models.sip_trunk import SIPTrunk  # noqa: F401
from new_phone.models.site import Site  # noqa: F401
from new_phone.models.sms import (  # noqa: F401
    Conversation,
    ConversationNote,
    Message,
    SMSOptOut,
    SMSProviderConfig,
)
from new_phone.models.tenant import Tenant  # noqa: F401
from new_phone.models.time_condition import TimeCondition  # noqa: F401
from new_phone.models.user import User  # noqa: F401
from new_phone.models.voicemail_box import VoicemailBox  # noqa: F401
from new_phone.models.voicemail_message import VoicemailMessage  # noqa: F401
from new_phone.models.workforce_management import (  # noqa: F401
    WfmForecastConfig,
    WfmScheduleEntry,
    WfmShift,
    WfmTimeOffRequest,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override URL from settings (admin user for migrations)
config.set_main_option("sqlalchemy.url", settings.admin_database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
