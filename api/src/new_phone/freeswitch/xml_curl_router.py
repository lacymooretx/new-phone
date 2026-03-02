"""FastAPI router for FreeSWITCH mod_xml_curl endpoints.

These endpoints return XML (not JSON) and are called by FreeSWITCH
over the internal Docker network. No JWT auth required.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Form, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from new_phone.auth.encryption import decrypt_value
from new_phone.db.engine import AdminSessionLocal
from new_phone.freeswitch.xml_builder import (
    build_callcenter_config,
    build_conference_config,
    build_dialplan,
    build_directory_user,
    build_gateway_config,
    build_not_found,
)
from new_phone.models.audio_prompt import AudioPrompt
from new_phone.models.caller_id_rule import CallerIdRule
from new_phone.models.camp_on import CampOnConfig
from new_phone.models.conference_bridge import ConferenceBridge
from new_phone.models.did import DID
from new_phone.models.extension import Extension
from new_phone.models.follow_me import FollowMe
from new_phone.models.holiday_calendar import HolidayCalendar
from new_phone.models.inbound_route import InboundRoute
from new_phone.models.ivr_menu import IVRMenu
from new_phone.models.outbound_route import OutboundRoute
from new_phone.models.page_group import PageGroup
from new_phone.models.paging_zone import PagingZone
from new_phone.models.parking_lot import ParkingLot
from new_phone.models.queue import Queue
from new_phone.models.ring_group import RingGroup
from new_phone.models.security_config import SecurityConfig
from new_phone.models.sip_trunk import SIPTrunk
from new_phone.models.tenant import Tenant
from new_phone.models.time_condition import TimeCondition
from new_phone.models.voicemail_box import VoicemailBox

logger = structlog.get_logger()

router = APIRouter(tags=["freeswitch"])

XML_CONTENT_TYPE = "text/xml; charset=utf-8"


@router.post("/freeswitch/directory")
async def xml_curl_directory(
    section: str = Form(""),
    action: str = Form(""),
    purpose: str = Form(""),
    key_value: str = Form(""),
    domain: str = Form(""),
    user: str = Form(""),
    sip_auth_username: str = Form(""),
    sip_auth_realm: str = Form(""),
) -> Response:
    """Handle FreeSWITCH directory lookups (SIP registration/auth)."""
    # FreeSWITCH may send username in different fields depending on context
    username = sip_auth_username or user or key_value
    lookup_domain = domain or sip_auth_realm

    logger.debug(
        "xml_curl_directory",
        username=username,
        domain=lookup_domain,
        action=action,
        purpose=purpose,
    )

    if not username or not lookup_domain:
        return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

    # Use AdminSession (bypasses RLS) since this is internal FS → API
    async with AdminSessionLocal() as session:
        ext = None
        tenant = None

        # Try lookup by sip_username first (globally unique, works for WebRTC
        # where domain may be "localhost" instead of the tenant sip_domain)
        result = await session.execute(
            select(Extension).where(
                Extension.sip_username == username,
                Extension.is_active.is_(True),
            )
        )
        ext = result.scalar_one_or_none()

        if ext:
            # Load tenant for this extension
            result = await session.execute(
                select(Tenant).where(Tenant.id == ext.tenant_id, Tenant.is_active.is_(True))
            )
            tenant = result.scalar_one_or_none()
        else:
            # Fall back to tenant sip_domain + extension_number lookup
            result = await session.execute(
                select(Tenant).where(Tenant.sip_domain == lookup_domain, Tenant.is_active.is_(True))
            )
            tenant = result.scalar_one_or_none()
            if tenant:
                result = await session.execute(
                    select(Extension).where(
                        Extension.tenant_id == tenant.id,
                        Extension.extension_number == username,
                        Extension.is_active.is_(True),
                    )
                )
                ext = result.scalar_one_or_none()

        if not tenant or not ext or not ext.encrypted_sip_password:
            logger.debug(
                "xml_curl_directory_not_found",
                username=username,
                domain=lookup_domain,
            )
            return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

        # Decrypt SIP password
        try:
            sip_password = decrypt_value(ext.encrypted_sip_password)
        except ValueError:
            logger.error("xml_curl_directory_decrypt_failed", ext_id=str(ext.id))
            return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

        # Load voicemail box if linked
        vm_box = None
        if ext.voicemail_box_id:
            result = await session.execute(
                select(VoicemailBox).where(VoicemailBox.id == ext.voicemail_box_id)
            )
            vm_box = result.scalar_one_or_none()

        xml = build_directory_user(ext, tenant, vm_box, sip_password, domain_override=lookup_domain)
        return Response(content=xml, media_type=XML_CONTENT_TYPE)


@router.post("/freeswitch/dialplan")
async def xml_curl_dialplan(
    section: str = Form(""),
    Caller_Context: str = Form("", alias="Caller-Context"),
    Caller_Destination_Number: str = Form("", alias="Destination-Number"),
    variable_sip_from_domain: str = Form(""),
    Hunt_Context: str = Form("", alias="Hunt-Context"),
) -> Response:
    """Handle FreeSWITCH dialplan lookups (call routing)."""
    context = Caller_Context or Hunt_Context

    logger.debug(
        "xml_curl_dialplan",
        context=context,
        destination=Caller_Destination_Number,
        domain=variable_sip_from_domain,
    )

    if not context:
        return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

    async with AdminSessionLocal() as session:
        # Find tenant by slug (context name = tenant slug)
        result = await session.execute(
            select(Tenant).where(Tenant.slug == context, Tenant.is_active.is_(True))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            logger.debug("xml_curl_dialplan_tenant_not_found", context=context)
            return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

        # Load all tenant data for dialplan generation
        extensions = list(
            (await session.execute(select(Extension).where(Extension.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        voicemail_boxes = list(
            (await session.execute(select(VoicemailBox).where(VoicemailBox.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        inbound_routes = list(
            (await session.execute(select(InboundRoute).where(InboundRoute.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        outbound_routes = list(
            (
                await session.execute(
                    select(OutboundRoute)
                    .where(OutboundRoute.tenant_id == tenant.id)
                    .options(selectinload(OutboundRoute.trunk_assignments))
                )
            )
            .scalars()
            .all()
        )

        ring_groups = list(
            (
                await session.execute(
                    select(RingGroup)
                    .where(RingGroup.tenant_id == tenant.id)
                    .options(selectinload(RingGroup.members))
                )
            )
            .scalars()
            .all()
        )

        trunks = list(
            (await session.execute(select(SIPTrunk).where(SIPTrunk.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        dids = list(
            (await session.execute(select(DID).where(DID.tenant_id == tenant.id))).scalars().all()
        )

        time_conditions = list(
            (
                await session.execute(
                    select(TimeCondition)
                    .where(TimeCondition.tenant_id == tenant.id)
                    .options(
                        selectinload(TimeCondition.holiday_calendar).selectinload(
                            HolidayCalendar.entries
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

        ivr_menus = list(
            (
                await session.execute(
                    select(IVRMenu)
                    .where(IVRMenu.tenant_id == tenant.id)
                    .options(selectinload(IVRMenu.options))
                )
            )
            .scalars()
            .all()
        )

        queues = list(
            (
                await session.execute(
                    select(Queue)
                    .where(Queue.tenant_id == tenant.id)
                    .options(selectinload(Queue.members))
                )
            )
            .scalars()
            .all()
        )

        conference_bridges = list(
            (
                await session.execute(
                    select(ConferenceBridge).where(ConferenceBridge.tenant_id == tenant.id)
                )
            )
            .scalars()
            .all()
        )

        page_groups_list = list(
            (
                await session.execute(
                    select(PageGroup)
                    .where(PageGroup.tenant_id == tenant.id)
                    .options(selectinload(PageGroup.members))
                )
            )
            .scalars()
            .all()
        )

        follow_me_list = list(
            (
                await session.execute(
                    select(FollowMe)
                    .where(FollowMe.tenant_id == tenant.id)
                    .options(selectinload(FollowMe.destinations))
                )
            )
            .scalars()
            .all()
        )

        # Load audio prompts for MOH resolution
        audio_prompts = list(
            (await session.execute(select(AudioPrompt).where(AudioPrompt.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        # Load caller ID rules
        caller_id_rules = list(
            (await session.execute(select(CallerIdRule).where(CallerIdRule.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        # Load parking lots
        parking_lots_list = list(
            (await session.execute(select(ParkingLot).where(ParkingLot.tenant_id == tenant.id)))
            .scalars()
            .all()
        )

        # Load security config
        security_config_result = await session.execute(
            select(SecurityConfig).where(
                SecurityConfig.tenant_id == tenant.id, SecurityConfig.is_active.is_(True)
            )
        )
        security_config = security_config_result.scalar_one_or_none()

        # Load paging zones
        paging_zones_list = list(
            (
                await session.execute(
                    select(PagingZone)
                    .where(PagingZone.tenant_id == tenant.id)
                    .options(selectinload(PagingZone.members))
                )
            )
            .scalars()
            .all()
        )

        # Load camp-on config
        camp_on_config_result = await session.execute(
            select(CampOnConfig).where(
                CampOnConfig.tenant_id == tenant.id, CampOnConfig.is_active.is_(True)
            )
        )
        camp_on_config = camp_on_config_result.scalar_one_or_none()

        xml = build_dialplan(
            tenant=tenant,
            extensions=extensions,
            inbound_routes=inbound_routes,
            outbound_routes=outbound_routes,
            ring_groups=ring_groups,
            voicemail_boxes=voicemail_boxes,
            trunks=trunks,
            dids=dids,
            time_conditions=time_conditions,
            ivr_menus=ivr_menus,
            queues=queues,
            conference_bridges=conference_bridges,
            page_groups=page_groups_list,
            follow_me_configs=follow_me_list,
            audio_prompts=audio_prompts,
            caller_id_rules=caller_id_rules,
            parking_lots=parking_lots_list,
            security_config=security_config,
            paging_zones=paging_zones_list,
            camp_on_config=camp_on_config,
        )
        return Response(content=xml, media_type=XML_CONTENT_TYPE)


@router.post("/freeswitch/configuration")
async def xml_curl_configuration(
    section: str = Form(""),
    key_value: str = Form(""),
    purpose: str = Form(""),
) -> Response:
    """Handle FreeSWITCH configuration lookups (gateway config, etc.)."""
    logger.debug(
        "xml_curl_configuration",
        key_value=key_value,
        purpose=purpose,
    )

    # Handle ivr.conf requests
    if key_value == "ivr.conf":
        return await _handle_ivr_config()

    # Handle callcenter.conf requests
    if key_value == "callcenter.conf":
        return await _handle_callcenter_config()

    # Handle conference.conf requests
    if key_value == "conference.conf":
        xml = build_conference_config()
        return Response(content=xml, media_type=XML_CONTENT_TYPE)

    # Only handle sofia.conf gateway requests
    if key_value != "sofia.conf":
        return Response(content=build_not_found(), media_type=XML_CONTENT_TYPE)

    async with AdminSessionLocal() as session:
        # Load all active trunks
        trunks = list(
            (await session.execute(select(SIPTrunk).where(SIPTrunk.is_active.is_(True))))
            .scalars()
            .all()
        )

        # Load all tenants for these trunks
        tenant_ids = {t.tenant_id for t in trunks}
        tenants_result = await session.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        tenants = {str(t.id): t for t in tenants_result.scalars().all()}

        # Decrypt trunk passwords
        passwords = {}
        for trunk in trunks:
            if trunk.encrypted_password:
                try:
                    passwords[str(trunk.id)] = decrypt_value(trunk.encrypted_password)
                except ValueError:
                    logger.error("xml_curl_config_decrypt_failed", trunk_id=str(trunk.id))

        xml = build_gateway_config(trunks, tenants, passwords)
        return Response(content=xml, media_type=XML_CONTENT_TYPE)


async def _handle_ivr_config() -> Response:
    """Build ivr.conf XML for all tenants' IVR menus."""
    from xml.etree.ElementTree import Element, SubElement, tostring

    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="configuration")
    config = SubElement(section, "configuration", name="ivr.conf", description="IVR menus")
    menus = SubElement(config, "menus")

    async with AdminSessionLocal() as session:
        # Load all active tenants
        tenants_result = await session.execute(select(Tenant).where(Tenant.is_active.is_(True)))
        tenants = list(tenants_result.scalars().all())

        for tenant in tenants:
            ivr_menus = list(
                (
                    await session.execute(
                        select(IVRMenu)
                        .where(IVRMenu.tenant_id == tenant.id, IVRMenu.is_active.is_(True))
                        .options(selectinload(IVRMenu.options))
                    )
                )
                .scalars()
                .all()
            )

            if not ivr_menus:
                continue

            # Load audio prompts for this tenant
            prompts_result = await session.execute(
                select(AudioPrompt).where(
                    AudioPrompt.tenant_id == tenant.id,
                    AudioPrompt.is_active.is_(True),
                )
            )
            prompt_map = {str(p.id): p for p in prompts_result.scalars().all()}

            # Build IVR menu elements for this tenant
            context_name = tenant.slug
            domain_name = tenant.sip_domain or f"{tenant.slug}.sip.local"

            for ivr in ivr_menus:
                if not ivr.enabled:
                    continue
                menu_name = f"{context_name}-ivr-{ivr.name.lower().replace(' ', '-')}"
                menu_attrs = {"name": menu_name}

                if ivr.greet_long_prompt_id:
                    p = prompt_map.get(str(ivr.greet_long_prompt_id))
                    if p and p.local_path:
                        menu_attrs["greet-long"] = p.local_path
                if ivr.greet_short_prompt_id:
                    p = prompt_map.get(str(ivr.greet_short_prompt_id))
                    if p and p.local_path:
                        menu_attrs["greet-short"] = p.local_path
                if ivr.invalid_sound_prompt_id:
                    p = prompt_map.get(str(ivr.invalid_sound_prompt_id))
                    if p and p.local_path:
                        menu_attrs["invalid-sound"] = p.local_path
                if ivr.exit_sound_prompt_id:
                    p = prompt_map.get(str(ivr.exit_sound_prompt_id))
                    if p and p.local_path:
                        menu_attrs["exit-sound"] = p.local_path

                menu_attrs["timeout"] = str(ivr.timeout * 1000)
                menu_attrs["max-failures"] = str(ivr.max_failures)
                menu_attrs["max-timeouts"] = str(ivr.max_timeouts)
                menu_attrs["inter-digit-timeout"] = str(ivr.inter_digit_timeout * 1000)
                menu_attrs["digit-len"] = str(ivr.digit_len)

                menu_el = SubElement(menus, "menu", **menu_attrs)

                for opt in sorted(ivr.options, key=lambda o: o.position):
                    from new_phone.freeswitch.xml_builder import _ivr_option_to_fs_action

                    entry_action = _ivr_option_to_fs_action(opt, context_name, domain_name)
                    if entry_action:
                        SubElement(
                            menu_el,
                            "entry",
                            action="menu-exec-app",
                            digits=opt.digits,
                            param=entry_action,
                        )

    raw = tostring(doc, encoding="unicode", xml_declaration=False)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{raw}'
    return Response(content=xml, media_type=XML_CONTENT_TYPE)


async def _handle_callcenter_config() -> Response:
    """Build callcenter.conf XML for all tenants' queues, agents, and tiers."""
    async with AdminSessionLocal() as session:
        # Load all active tenants
        tenants_result = await session.execute(select(Tenant).where(Tenant.is_active.is_(True)))
        tenants = list(tenants_result.scalars().all())

        queues_by_tenant: dict[str, list] = {}
        extensions_by_tenant: dict[str, list] = {}
        prompt_map: dict[str, object] = {}

        for tenant in tenants:
            tid = str(tenant.id)

            # Load queues with members
            queues = list(
                (
                    await session.execute(
                        select(Queue)
                        .where(Queue.tenant_id == tenant.id, Queue.is_active.is_(True))
                        .options(selectinload(Queue.members))
                    )
                )
                .scalars()
                .all()
            )
            if not queues:
                continue

            queues_by_tenant[tid] = queues

            # Load extensions for agent contact strings
            extensions = list(
                (await session.execute(select(Extension).where(Extension.tenant_id == tenant.id)))
                .scalars()
                .all()
            )
            extensions_by_tenant[tid] = extensions

            # Load audio prompts for MOH
            prompts_result = await session.execute(
                select(AudioPrompt).where(
                    AudioPrompt.tenant_id == tenant.id,
                    AudioPrompt.is_active.is_(True),
                )
            )
            for p in prompts_result.scalars().all():
                prompt_map[str(p.id)] = p

        xml = build_callcenter_config(tenants, queues_by_tenant, extensions_by_tenant, prompt_map)
        return Response(content=xml, media_type=XML_CONTENT_TYPE)


@router.post("/internal/camp-on/create")
async def internal_camp_on_create(
    tenant_slug: str = Form(""),
    caller_extension_number: str = Form(""),
    target_extension_number: str = Form(""),
    reason: str = Form("busy"),
    original_call_id: str = Form(""),
) -> Response:
    """Internal endpoint for FreeSWITCH to create camp-on requests.

    Called from dialplan via mod_curl. No JWT auth (FS internal network only).
    """
    if not tenant_slug or not caller_extension_number or not target_extension_number:
        return Response(content="ERROR: missing parameters", media_type="text/plain")

    # Normalize reason from FS originate_disposition
    normalized_reason = "busy" if "BUSY" in reason.upper() else "no_answer"

    async with AdminSessionLocal() as session:
        # Resolve tenant
        result = await session.execute(
            select(Tenant).where(Tenant.slug == tenant_slug, Tenant.is_active.is_(True))
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return Response(content="ERROR: tenant not found", media_type="text/plain")

        from new_phone.main import redis_client
        from new_phone.schemas.camp_on import CampOnCreateRequest
        from new_phone.services.camp_on_service import CampOnService

        service = CampOnService(session, redis=redis_client)
        try:
            data = CampOnCreateRequest(
                caller_extension_number=caller_extension_number,
                target_extension_number=target_extension_number,
                reason=normalized_reason,
                original_call_id=original_call_id or None,
            )
            await service.create_request(tenant.id, data)
        except ValueError as e:
            logger.warning(
                "camp_on_create_rejected",
                tenant=tenant_slug,
                caller=caller_extension_number,
                target=target_extension_number,
                error=str(e),
            )
            return Response(content=f"ERROR: {e}", media_type="text/plain")

    return Response(content="OK", media_type="text/plain")
