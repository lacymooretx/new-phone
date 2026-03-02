from enum import StrEnum

from new_phone.models.user import UserRole


class Permission(StrEnum):
    # Platform-level
    MANAGE_PLATFORM = "manage_platform"
    VIEW_ALL_TENANTS = "view_all_tenants"

    # Tenant management
    MANAGE_TENANT = "manage_tenant"
    VIEW_TENANT = "view_tenant"

    # User management
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"

    # Self-service
    VIEW_OWN_PROFILE = "view_own_profile"
    EDIT_OWN_PROFILE = "edit_own_profile"

    # Telephony — Extensions
    MANAGE_EXTENSIONS = "manage_extensions"
    VIEW_EXTENSIONS = "view_extensions"

    # Telephony — SIP Trunks
    MANAGE_TRUNKS = "manage_trunks"
    VIEW_TRUNKS = "view_trunks"

    # Telephony — DIDs
    MANAGE_DIDS = "manage_dids"
    VIEW_DIDS = "view_dids"

    # Telephony — Inbound Routes
    MANAGE_INBOUND_ROUTES = "manage_inbound_routes"
    VIEW_INBOUND_ROUTES = "view_inbound_routes"

    # Telephony — Outbound Routes
    MANAGE_OUTBOUND_ROUTES = "manage_outbound_routes"
    VIEW_OUTBOUND_ROUTES = "view_outbound_routes"

    # Telephony — Ring Groups
    MANAGE_RING_GROUPS = "manage_ring_groups"
    VIEW_RING_GROUPS = "view_ring_groups"

    # Telephony — Voicemail
    MANAGE_VOICEMAIL = "manage_voicemail"
    VIEW_VOICEMAIL = "view_voicemail"

    # CDR & Recordings
    VIEW_CDRS = "view_cdrs"
    MANAGE_RECORDINGS = "manage_recordings"
    VIEW_RECORDINGS = "view_recordings"

    # Voicemail Messages
    MANAGE_VOICEMAIL_MESSAGES = "manage_voicemail_messages"
    VIEW_VOICEMAIL_MESSAGES = "view_voicemail_messages"

    # IVR / Time Conditions / Audio Prompts
    MANAGE_IVR = "manage_ivr"
    VIEW_IVR = "view_ivr"

    # Call Queues (ACD)
    MANAGE_QUEUES = "manage_queues"
    VIEW_QUEUES = "view_queues"

    # Conference Bridges
    MANAGE_CONFERENCES = "manage_conferences"
    VIEW_CONFERENCES = "view_conferences"

    # Paging / Intercom
    MANAGE_PAGING = "manage_paging"
    VIEW_PAGING = "view_paging"

    # Devices / Phone Provisioning
    MANAGE_DEVICES = "manage_devices"
    VIEW_DEVICES = "view_devices"

    # SMS / Messaging
    MANAGE_SMS = "manage_sms"
    VIEW_SMS = "view_sms"

    # Audit Logs
    VIEW_AUDIT_LOGS = "view_audit_logs"

    # AI Voice Agents
    MANAGE_AI_AGENTS = "manage_ai_agents"
    VIEW_AI_AGENTS = "view_ai_agents"

    # TCPA Compliance
    MANAGE_COMPLIANCE = "manage_compliance"
    VIEW_COMPLIANCE = "view_compliance"

    # Workforce Management
    MANAGE_WFM = "manage_wfm"
    VIEW_WFM = "view_wfm"

    # Click-to-Call
    PLACE_CALLS = "place_calls"

    # Emergency & Physical Security
    MANAGE_SECURITY = "manage_security"
    VIEW_SECURITY = "view_security"
    TRIGGER_PANIC = "trigger_panic"
    MANAGE_PANIC_ALERTS = "manage_panic_alerts"
    SECURITY_LISTEN = "security_listen"
    MANAGE_DOOR_STATIONS = "manage_door_stations"
    VIEW_DOOR_STATIONS = "view_door_stations"
    TRIGGER_DOOR_UNLOCK = "trigger_door_unlock"
    MANAGE_PAGING_ZONES = "manage_paging_zones"
    VIEW_PAGING_ZONES = "view_paging_zones"
    MANAGE_BUILDING_WEBHOOKS = "manage_building_webhooks"
    VIEW_BUILDING_WEBHOOKS = "view_building_webhooks"


# Role → permissions mapping
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    UserRole.MSP_SUPER_ADMIN: {
        Permission.MANAGE_PLATFORM,
        Permission.VIEW_ALL_TENANTS,
        Permission.MANAGE_TENANT,
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_EXTENSIONS,
        Permission.VIEW_EXTENSIONS,
        Permission.MANAGE_TRUNKS,
        Permission.VIEW_TRUNKS,
        Permission.MANAGE_DIDS,
        Permission.VIEW_DIDS,
        Permission.MANAGE_INBOUND_ROUTES,
        Permission.VIEW_INBOUND_ROUTES,
        Permission.MANAGE_OUTBOUND_ROUTES,
        Permission.VIEW_OUTBOUND_ROUTES,
        Permission.MANAGE_RING_GROUPS,
        Permission.VIEW_RING_GROUPS,
        Permission.MANAGE_VOICEMAIL,
        Permission.VIEW_VOICEMAIL,
        Permission.VIEW_CDRS,
        Permission.MANAGE_RECORDINGS,
        Permission.VIEW_RECORDINGS,
        Permission.MANAGE_VOICEMAIL_MESSAGES,
        Permission.VIEW_VOICEMAIL_MESSAGES,
        Permission.MANAGE_IVR,
        Permission.VIEW_IVR,
        Permission.MANAGE_QUEUES,
        Permission.VIEW_QUEUES,
        Permission.MANAGE_CONFERENCES,
        Permission.VIEW_CONFERENCES,
        Permission.MANAGE_PAGING,
        Permission.VIEW_PAGING,
        Permission.MANAGE_DEVICES,
        Permission.VIEW_DEVICES,
        Permission.MANAGE_SMS,
        Permission.VIEW_SMS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_AI_AGENTS,
        Permission.VIEW_AI_AGENTS,
        Permission.MANAGE_COMPLIANCE,
        Permission.VIEW_COMPLIANCE,
        Permission.MANAGE_WFM,
        Permission.VIEW_WFM,
        Permission.PLACE_CALLS,
        Permission.MANAGE_SECURITY,
        Permission.VIEW_SECURITY,
        Permission.TRIGGER_PANIC,
        Permission.MANAGE_PANIC_ALERTS,
        Permission.SECURITY_LISTEN,
        Permission.MANAGE_DOOR_STATIONS,
        Permission.VIEW_DOOR_STATIONS,
        Permission.TRIGGER_DOOR_UNLOCK,
        Permission.MANAGE_PAGING_ZONES,
        Permission.VIEW_PAGING_ZONES,
        Permission.MANAGE_BUILDING_WEBHOOKS,
        Permission.VIEW_BUILDING_WEBHOOKS,
    },
    UserRole.MSP_TECH: {
        Permission.VIEW_ALL_TENANTS,
        Permission.MANAGE_TENANT,
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_EXTENSIONS,
        Permission.VIEW_EXTENSIONS,
        Permission.MANAGE_TRUNKS,
        Permission.VIEW_TRUNKS,
        Permission.MANAGE_DIDS,
        Permission.VIEW_DIDS,
        Permission.MANAGE_INBOUND_ROUTES,
        Permission.VIEW_INBOUND_ROUTES,
        Permission.MANAGE_OUTBOUND_ROUTES,
        Permission.VIEW_OUTBOUND_ROUTES,
        Permission.MANAGE_RING_GROUPS,
        Permission.VIEW_RING_GROUPS,
        Permission.MANAGE_VOICEMAIL,
        Permission.VIEW_VOICEMAIL,
        Permission.VIEW_CDRS,
        Permission.MANAGE_RECORDINGS,
        Permission.VIEW_RECORDINGS,
        Permission.MANAGE_VOICEMAIL_MESSAGES,
        Permission.VIEW_VOICEMAIL_MESSAGES,
        Permission.MANAGE_IVR,
        Permission.VIEW_IVR,
        Permission.MANAGE_QUEUES,
        Permission.VIEW_QUEUES,
        Permission.MANAGE_CONFERENCES,
        Permission.VIEW_CONFERENCES,
        Permission.MANAGE_PAGING,
        Permission.VIEW_PAGING,
        Permission.MANAGE_DEVICES,
        Permission.VIEW_DEVICES,
        Permission.MANAGE_SMS,
        Permission.VIEW_SMS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_AI_AGENTS,
        Permission.VIEW_AI_AGENTS,
        Permission.MANAGE_COMPLIANCE,
        Permission.VIEW_COMPLIANCE,
        Permission.MANAGE_WFM,
        Permission.VIEW_WFM,
        Permission.PLACE_CALLS,
        Permission.MANAGE_SECURITY,
        Permission.VIEW_SECURITY,
        Permission.TRIGGER_PANIC,
        Permission.MANAGE_PANIC_ALERTS,
        Permission.MANAGE_DOOR_STATIONS,
        Permission.VIEW_DOOR_STATIONS,
        Permission.TRIGGER_DOOR_UNLOCK,
        Permission.MANAGE_PAGING_ZONES,
        Permission.VIEW_PAGING_ZONES,
        Permission.MANAGE_BUILDING_WEBHOOKS,
        Permission.VIEW_BUILDING_WEBHOOKS,
    },
    UserRole.TENANT_ADMIN: {
        Permission.MANAGE_TENANT,
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_EXTENSIONS,
        Permission.VIEW_EXTENSIONS,
        Permission.MANAGE_TRUNKS,
        Permission.VIEW_TRUNKS,
        Permission.MANAGE_DIDS,
        Permission.VIEW_DIDS,
        Permission.MANAGE_INBOUND_ROUTES,
        Permission.VIEW_INBOUND_ROUTES,
        Permission.MANAGE_OUTBOUND_ROUTES,
        Permission.VIEW_OUTBOUND_ROUTES,
        Permission.MANAGE_RING_GROUPS,
        Permission.VIEW_RING_GROUPS,
        Permission.MANAGE_VOICEMAIL,
        Permission.VIEW_VOICEMAIL,
        Permission.VIEW_CDRS,
        Permission.MANAGE_RECORDINGS,
        Permission.VIEW_RECORDINGS,
        Permission.MANAGE_VOICEMAIL_MESSAGES,
        Permission.VIEW_VOICEMAIL_MESSAGES,
        Permission.MANAGE_IVR,
        Permission.VIEW_IVR,
        Permission.MANAGE_QUEUES,
        Permission.VIEW_QUEUES,
        Permission.MANAGE_CONFERENCES,
        Permission.VIEW_CONFERENCES,
        Permission.MANAGE_PAGING,
        Permission.VIEW_PAGING,
        Permission.MANAGE_DEVICES,
        Permission.VIEW_DEVICES,
        Permission.MANAGE_SMS,
        Permission.VIEW_SMS,
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_AI_AGENTS,
        Permission.VIEW_AI_AGENTS,
        Permission.MANAGE_COMPLIANCE,
        Permission.VIEW_COMPLIANCE,
        Permission.MANAGE_WFM,
        Permission.VIEW_WFM,
        Permission.PLACE_CALLS,
        Permission.MANAGE_SECURITY,
        Permission.VIEW_SECURITY,
        Permission.TRIGGER_PANIC,
        Permission.MANAGE_PANIC_ALERTS,
        Permission.MANAGE_DOOR_STATIONS,
        Permission.VIEW_DOOR_STATIONS,
        Permission.TRIGGER_DOOR_UNLOCK,
        Permission.MANAGE_PAGING_ZONES,
        Permission.VIEW_PAGING_ZONES,
        Permission.MANAGE_BUILDING_WEBHOOKS,
        Permission.VIEW_BUILDING_WEBHOOKS,
    },
    UserRole.TENANT_MANAGER: {
        Permission.VIEW_TENANT,
        Permission.MANAGE_USERS,
        Permission.VIEW_USERS,
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.MANAGE_EXTENSIONS,
        Permission.VIEW_EXTENSIONS,
        Permission.VIEW_TRUNKS,
        Permission.VIEW_DIDS,
        Permission.VIEW_INBOUND_ROUTES,
        Permission.VIEW_OUTBOUND_ROUTES,
        Permission.MANAGE_RING_GROUPS,
        Permission.VIEW_RING_GROUPS,
        Permission.MANAGE_VOICEMAIL,
        Permission.VIEW_VOICEMAIL,
        Permission.VIEW_CDRS,
        Permission.MANAGE_RECORDINGS,
        Permission.VIEW_RECORDINGS,
        Permission.MANAGE_VOICEMAIL_MESSAGES,
        Permission.VIEW_VOICEMAIL_MESSAGES,
        Permission.VIEW_IVR,
        Permission.VIEW_QUEUES,
        Permission.VIEW_CONFERENCES,
        Permission.VIEW_PAGING,
        Permission.VIEW_DEVICES,
        Permission.VIEW_SMS,
        Permission.VIEW_AI_AGENTS,
        Permission.MANAGE_COMPLIANCE,
        Permission.VIEW_COMPLIANCE,
        Permission.MANAGE_WFM,
        Permission.VIEW_WFM,
        Permission.PLACE_CALLS,
        Permission.VIEW_SECURITY,
        Permission.TRIGGER_PANIC,
        Permission.TRIGGER_DOOR_UNLOCK,
        Permission.VIEW_DOOR_STATIONS,
        Permission.VIEW_PAGING_ZONES,
        Permission.VIEW_BUILDING_WEBHOOKS,
    },
    UserRole.TENANT_USER: {
        Permission.VIEW_OWN_PROFILE,
        Permission.EDIT_OWN_PROFILE,
        Permission.VIEW_EXTENSIONS,
        Permission.VIEW_RING_GROUPS,
        Permission.VIEW_VOICEMAIL,
        Permission.VIEW_CDRS,
        Permission.VIEW_RECORDINGS,
        Permission.VIEW_VOICEMAIL_MESSAGES,
        Permission.VIEW_SMS,
        Permission.VIEW_WFM,
        Permission.PLACE_CALLS,
        Permission.TRIGGER_PANIC,
        Permission.TRIGGER_DOOR_UNLOCK,
        Permission.VIEW_PAGING_ZONES,
    },
}

# Roles that can see/manage across tenants
MSP_ROLES = {UserRole.MSP_SUPER_ADMIN, UserRole.MSP_TECH}


def has_permission(role: str, permission: Permission) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms


def is_msp_role(role: str) -> bool:
    return role in MSP_ROLES
