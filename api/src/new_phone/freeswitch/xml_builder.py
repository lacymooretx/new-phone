"""Pure functions for generating FreeSWITCH XML configuration.

These functions take model data and return XML strings for mod_xml_curl responses.
No database access, no side effects — just data → XML.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element, SubElement, tostring

if TYPE_CHECKING:
    from new_phone.models.audio_prompt import AudioPrompt
    from new_phone.models.caller_id_rule import CallerIdRule
    from new_phone.models.camp_on import CampOnConfig
    from new_phone.models.conference_bridge import ConferenceBridge
    from new_phone.models.did import DID
    from new_phone.models.extension import Extension
    from new_phone.models.follow_me import FollowMe
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


def build_not_found() -> str:
    """Standard 'not found' XML response for mod_xml_curl."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n<document type="freeswitch/xml">\n  <section name="result">\n    <result status="not found"/>\n  </section>\n</document>'


def build_directory_user(
    extension: Extension,
    tenant: Tenant,
    voicemail_box: VoicemailBox | None,
    sip_password: str,
    domain_override: str | None = None,
) -> str:
    """Generate directory XML for a single user (SIP registration/auth).

    Args:
        extension: The extension model with user config.
        tenant: The tenant owning this extension.
        voicemail_box: Optional linked voicemail box.
        sip_password: Decrypted SIP password (plaintext).
        domain_override: If set, use this as the XML domain name instead of
            the tenant's sip_domain. Needed for WebRTC clients that register
            with "localhost" rather than the tenant's SIP domain.
    """
    domain_name = domain_override or tenant.sip_domain or f"{tenant.slug}.sip.local"

    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="directory")
    domain = SubElement(section, "domain", name=domain_name)

    # Domain params
    params = SubElement(domain, "params")
    _param(
        params,
        "dial-string",
        "{^^:sip_invite_domain=${dialed_domain}:presence_id=${dialed_user}@${dialed_domain}}${sofia_contact(*/{{dialed_user}}@${dialed_domain})}",
    )

    # User — id must match the SIP username used in REGISTER
    user = SubElement(domain, "user", id=extension.sip_username)

    # User params
    user_params = SubElement(user, "params")
    _param(user_params, "password", sip_password)
    _param(user_params, "vm-password", _get_vm_password(voicemail_box))
    _param(user_params, "max-registrations", str(extension.max_registrations))

    # User variables
    variables = SubElement(user, "variables")
    _var(variables, "toll_allow", _toll_allow(extension.class_of_service))
    _var(variables, "user_context", tenant.slug)
    _var(
        variables,
        "effective_caller_id_name",
        extension.internal_cid_name or extension.extension_number,
    )
    _var(
        variables,
        "effective_caller_id_number",
        extension.internal_cid_number or extension.extension_number,
    )
    if extension.external_cid_name:
        _var(variables, "outbound_caller_id_name", extension.external_cid_name)
    if extension.external_cid_number:
        _var(variables, "outbound_caller_id_number", extension.external_cid_number)
    _var(variables, "call_timeout", str(extension.call_forward_ring_time))
    if extension.dnd_enabled:
        _var(variables, "do_not_disturb", "true")
    if extension.call_forward_unconditional:
        _var(variables, "forward_immediate", extension.call_forward_unconditional)
    if extension.call_forward_busy:
        _var(variables, "forward_busy", extension.call_forward_busy)
    if extension.call_forward_no_answer:
        _var(variables, "forward_no_answer", extension.call_forward_no_answer)
    if extension.call_forward_not_registered:
        _var(variables, "forward_user_not_registered", extension.call_forward_not_registered)
    if voicemail_box:
        _var(variables, "mailbox", voicemail_box.mailbox_number)
    if not extension.call_waiting:
        _var(variables, "call_waiting", "false")
    if extension.pickup_group:
        _var(variables, "pickup_group", extension.pickup_group)
    _var(variables, "accountcode", tenant.slug)

    return _xml_to_string(doc)


def build_dialplan(
    tenant: Tenant,
    extensions: list[Extension],
    inbound_routes: list[InboundRoute],
    outbound_routes: list[OutboundRoute],
    ring_groups: list[RingGroup],
    voicemail_boxes: list[VoicemailBox],
    trunks: list[SIPTrunk],
    dids: list[DID],
    time_conditions: list[TimeCondition] | None = None,
    ivr_menus: list[IVRMenu] | None = None,
    queues: list[Queue] | None = None,
    conference_bridges: list[ConferenceBridge] | None = None,
    page_groups: list[PageGroup] | None = None,
    follow_me_configs: list[FollowMe] | None = None,
    audio_prompts: list[AudioPrompt] | None = None,
    caller_id_rules: list[CallerIdRule] | None = None,
    parking_lots: list[ParkingLot] | None = None,
    security_config: SecurityConfig | None = None,
    paging_zones: list[PagingZone] | None = None,
    camp_on_config: CampOnConfig | None = None,
) -> str:
    """Generate full dialplan context XML for a tenant.

    Produces extensions in priority order:
    1. Feature codes (*97, *78/*79, *72/*73, *50/*51/*52, *85/*86, *80, *8, **)
    2. Parking slot retrieval (direct dial slot numbers)
    3. Local extensions (with hash-insert for directed pickup)
    4. Ring groups
    4.5. Queue routing
    5. Conference bridges
    5.5. Page groups
    6. Direct-to-voicemail (*ext)
    7. Time condition routing
    7.5. Caller ID blocklist/allowlist
    8. Inbound routes (DID → destination)
    9. Outbound routes (by priority)
    """
    domain_name = tenant.sip_domain or f"{tenant.slug}.sip.local"
    context_name = tenant.slug

    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="dialplan")
    context = SubElement(section, "context", name=context_name)

    # Build lookup maps
    ext_map = {str(e.id): e for e in extensions}
    vm_map = {str(v.id): v for v in voicemail_boxes}
    did_map = {str(d.id): d for d in dids}
    trunk_map = {str(t.id): t for t in trunks}
    ivr_map = {str(m.id): m for m in (ivr_menus or [])}
    queue_map = {str(q.id): q for q in (queues or [])}
    conference_map = {str(cb.id): cb for cb in (conference_bridges or [])}
    tc_list = [tc for tc in (time_conditions or []) if tc.enabled and tc.is_active]
    fm_map = {
        str(fm.extension_id): fm for fm in (follow_me_configs or []) if fm.enabled and fm.is_active
    }
    prompt_map = {str(p.id): p for p in (audio_prompts or [])}
    # Also build ext_number → ext_id map for follow-me internal destination detection
    ext_number_map = {e.extension_number: e for e in extensions if e.is_active}

    # Resolve tenant default MOH path
    tenant_default_moh_path = None
    if hasattr(tenant, "default_moh_prompt_id") and tenant.default_moh_prompt_id:
        moh_prompt = prompt_map.get(str(tenant.default_moh_prompt_id))
        if moh_prompt and moh_prompt.local_path:
            tenant_default_moh_path = moh_prompt.local_path

    # Active parking lots for this tenant
    active_parking_lots = [pl for pl in (parking_lots or []) if pl.is_active]

    # 1. Feature codes (includes *85 park, *86XX retrieve)
    _add_feature_codes(context, domain_name, vm_map, extensions)

    # 1.5. Parking feature codes
    _add_parking_feature_codes(context, domain_name, active_parking_lots)

    # 2. Parking slot direct retrieval (dial the slot number to retrieve)
    _add_parking_slot_retrieval(context, domain_name, active_parking_lots)

    # 1.7. Security feature codes (*0911 panic, *0999 emergency allcall)
    _add_security_feature_codes(context, domain_name, security_config)

    # 1.8. Paging zone extensions
    _add_paging_zone_extensions(context, domain_name, context_name, paging_zones)

    # 1.9. Camp-on feature codes and handler
    _add_camp_on_feature_codes(context, domain_name, context_name, camp_on_config)

    # 3. Local extensions (with hash-insert for directed pickup)
    for ext in extensions:
        if not ext.is_active:
            continue
        dp_ext = SubElement(context, "extension", name=f"local-{ext.extension_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(ext.extension_number)}$")
        cond = dp_ext.find("condition")

        # DND check
        if ext.dnd_enabled:
            _action(cond, "respond", "480 Temporarily Unavailable")
        else:
            # Recording policy
            _add_recording_actions(cond, ext)

            # Set dialed_extension and hash-insert for directed pickup tracking
            _action(cond, "set", f"dialed_extension={ext.extension_number}")
            _action(
                cond,
                "hash",
                f"insert/${{domain_name}}-call_return/{ext.extension_number}/${{uuid}}",
            )

            # Call forward unconditional
            if ext.call_forward_unconditional:
                _action(cond, "bridge", f"user/{ext.call_forward_unconditional}@{domain_name}")
            else:
                _action(cond, "set", f"call_timeout={ext.call_forward_ring_time}")
                _action(cond, "set", "hangup_after_bridge=true")
                _action(cond, "set", "continue_on_fail=true")

                bridge_str = f"user/{ext.extension_number}@{domain_name}"
                _action(cond, "bridge", bridge_str)

                # Follow-me: try external destinations before voicemail
                fm = fm_map.get(str(ext.id))
                if fm and fm.destinations:
                    _add_follow_me_bridges(cond, fm, ext_number_map, domain_name, context_name)

                # Camp-on offer: after failed bridge, before voicemail
                if camp_on_config and camp_on_config.enabled and camp_on_config.is_active:
                    _action(cond, "answer")
                    _action(
                        cond,
                        "play_and_get_digits",
                        "1 1 1 5000 # "
                        "ivr/ivr-please_press_one.wav silence_stream://250 "
                        "campon_choice \\d",
                    )
                    _action(
                        cond,
                        "execute_extension",
                        f"camp-on-handler-${{campon_choice}} XML {context_name}",
                    )

                # On no answer, go to voicemail if available
                vm_box = vm_map.get(str(ext.voicemail_box_id)) if ext.voicemail_box_id else None
                if vm_box and vm_box.is_active:
                    if not (camp_on_config and camp_on_config.enabled and camp_on_config.is_active):
                        _action(cond, "answer")
                    _action(cond, "voicemail", f"default {domain_name} {vm_box.mailbox_number}")

    # 3. Ring groups
    for rg in ring_groups:
        if not rg.is_active:
            continue
        dp_ext = SubElement(context, "extension", name=f"ring-group-{rg.group_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(rg.group_number)}$")
        cond = dp_ext.find("condition")

        _action(cond, "set", f"call_timeout={rg.ring_time}")
        _action(cond, "set", "hangup_after_bridge=true")
        _action(cond, "set", "continue_on_fail=true")

        # Music on Hold for ring group
        moh_path = _resolve_moh_path(
            getattr(rg, "moh_prompt_id", None), prompt_map, tenant_default_moh_path
        )
        if moh_path:
            _action(cond, "set", f"hold_music={moh_path}")

        bridge_str = _ring_group_bridge_string(rg, ext_map, domain_name)
        if bridge_str:
            _action(cond, "bridge", bridge_str)

        # Ring group failover
        if rg.failover_dest_type == "voicemail" and rg.failover_dest_id:
            fvm = vm_map.get(str(rg.failover_dest_id))
            if fvm:
                _action(cond, "answer")
                _action(cond, "voicemail", f"default {domain_name} {fvm.mailbox_number}")

    # 3.5. Queue routing
    for q in queues or []:
        if not q.is_active or not q.enabled:
            continue
        queue_fs_name = f"{context_name}-{q.name.lower().replace(' ', '-')}"
        dp_ext = SubElement(context, "extension", name=f"queue-{q.queue_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(q.queue_number)}$")
        cond = dp_ext.find("condition")
        # Music on Hold for queue
        moh_path = _resolve_moh_path(
            getattr(q, "moh_prompt_id", None), prompt_map, tenant_default_moh_path
        )
        if moh_path:
            _action(cond, "set", f"hold_music={moh_path}")

        _action(cond, "set", "hangup_after_bridge=true")
        _action(cond, "set", "continue_on_fail=true")
        _action(cond, "callcenter", queue_fs_name)

    # 4. Conference bridges
    for cb in conference_bridges or []:
        if not cb.is_active or not cb.enabled:
            continue
        conf_name = f"{context_name}-conf-{cb.room_number}"
        dp_ext = SubElement(context, "extension", name=f"conference-{cb.room_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(cb.room_number)}$")
        cond = dp_ext.find("condition")
        _action(cond, "answer")
        if cb.max_participants and cb.max_participants > 0:
            _action(cond, "set", f"conference_max_members={cb.max_participants}")
        if cb.participant_pin:
            _action(cond, "set", f"conference_pin={cb.participant_pin}")
        if cb.moderator_pin:
            _action(cond, "set", f"conference_moderator_pin={cb.moderator_pin}")
        # Conference MOH
        if cb.moh_prompt_id:
            prompt = prompt_map.get(str(cb.moh_prompt_id))
            if prompt and prompt.local_path:
                _action(cond, "set", f"conference_moh_sound={prompt.local_path}")
        if cb.record_conference:
            _action(
                cond,
                "set",
                "auto-record=/recordings/${accountcode}/conf-${strftime(%Y%m%d-%H%M%S)}-${uuid}.wav",
            )
        # Build conference flags
        flags = ["waste"]
        if cb.wait_for_moderator:
            flags.append("waitmod")
        if cb.muted_on_join:
            flags.append("mute")
        flag_str = "|".join(flags)
        _action(cond, "conference", f"{conf_name}@default+flags{{{flag_str}}}")

    # 4.5. Page groups
    for pg in page_groups or []:
        if not pg.is_active:
            continue
        page_conf_name = f"{context_name}-page-{pg.page_number}"
        dp_ext = SubElement(context, "extension", name=f"page-{pg.page_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(pg.page_number)}$")
        cond = dp_ext.find("condition")
        _action(cond, "answer")
        _action(cond, "set", f"conference_auto_outcall_timeout={pg.timeout}")
        # Add auto-outcall for each member
        for member in sorted(pg.members, key=lambda m: m.position):
            ext = ext_map.get(str(member.extension_id))
            if ext and ext.is_active:
                outcall_str = (
                    f"{{sip_auto_answer=true,sip_h_Call-Info=<sip:>;answer-after=0}}"
                    f"user/{ext.extension_number}@{domain_name}"
                )
                _action(cond, "conference_set_auto_outcall", outcall_str)
        # Conference with flags
        page_flags = ["waste"]
        if pg.page_mode == "one_way":
            page_flags.append("mute")
        flag_str = "|".join(page_flags)
        _action(cond, "conference", f"{page_conf_name}@default+flags{{{flag_str}}}")

    # 5. Direct-to-voicemail (*ext for each ext with VM)
    for ext in extensions:
        if not ext.is_active or not ext.voicemail_box_id:
            continue
        vm_box = vm_map.get(str(ext.voicemail_box_id))
        if not vm_box or not vm_box.is_active:
            continue
        dp_ext = SubElement(context, "extension", name=f"direct-vm-{ext.extension_number}")
        _condition(dp_ext, "destination_number", f"^\\*{re.escape(ext.extension_number)}$")
        cond = dp_ext.find("condition")
        _action(cond, "answer")
        _action(cond, "voicemail", f"default {domain_name} {vm_box.mailbox_number}")

    # 6. Time condition routing (with holiday preemption and manual override)
    rg_map = {str(r.id): r for r in ring_groups}
    for tc in tc_list:
        _add_time_condition_extension(
            context,
            tc,
            ext_map,
            vm_map,
            rg_map=rg_map,
            domain_name=domain_name,
            context_name=context_name,
            ivr_map=ivr_map,
            queue_map=queue_map,
            conference_map=conference_map,
        )

    # 6.5. Caller ID blocklist/allowlist
    _add_blocklist_extensions(context, caller_id_rules or [], vm_map, domain_name, context_name)

    # 7. Inbound routes (DID → destination)
    for route in inbound_routes:
        if not route.enabled or not route.is_active or not route.did_id:
            continue
        did = did_map.get(str(route.did_id))
        if not did:
            continue

        dp_ext = SubElement(context, "extension", name=f"inbound-{did.number}")
        # Match the DID number (strip leading +)
        did_pattern = re.escape(did.number.lstrip("+"))
        _condition(dp_ext, "destination_number", f"^\\+?{did_pattern}$")
        cond = dp_ext.find("condition")

        if route.cid_name_prefix:
            _action(
                cond, "set", f"effective_caller_id_name={route.cid_name_prefix} ${{caller_id_name}}"
            )

        _add_inbound_destination(
            cond,
            route,
            ext_map,
            vm_map,
            rg_map=rg_map,
            domain_name=domain_name,
            context_name=context_name,
            ivr_map=ivr_map,
            queue_map=queue_map,
            conference_map=conference_map,
        )

    # 8. Outbound routes (sorted by priority)
    sorted_routes = sorted(
        [r for r in outbound_routes if r.enabled and r.is_active],
        key=lambda r: r.priority,
    )
    for route in sorted_routes:
        dp_ext = SubElement(
            context, "extension", name=f"outbound-{route.name.lower().replace(' ', '-')}"
        )
        pattern = _dial_pattern_to_regex(route.dial_pattern)
        _condition(dp_ext, "destination_number", pattern)
        cond = dp_ext.find("condition")

        _action(cond, "set", "hangup_after_bridge=true")

        # Strip/prepend logic
        if route.strip_digits > 0:
            _action(cond, "set", f"dialed_number=${{destination_number::{route.strip_digits}}}")
        else:
            _action(cond, "set", "dialed_number=${destination_number}")

        if route.prepend_digits:
            _action(cond, "set", f"dialed_number={route.prepend_digits}${{dialed_number}}")

        # Build trunk bridge string with failover
        bridge_parts = _outbound_trunk_bridge(route, trunk_map, tenant)
        if bridge_parts:
            _action(cond, "bridge", bridge_parts)

    return _xml_to_string(doc)


def build_gateway_config(
    trunks: list[SIPTrunk], tenants: dict[str, Tenant], passwords: dict[str, str]
) -> str:
    """Generate sofia gateway XML for all active SIP trunks.

    Args:
        trunks: Active SIP trunks.
        tenants: Map of tenant_id → Tenant.
        passwords: Map of trunk_id → decrypted password.
    """
    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="configuration")
    config = SubElement(section, "configuration", name="sofia.conf", description="sofia config")
    profiles = SubElement(config, "profiles")
    profile = SubElement(profiles, "profile", name="tls")
    gateways = SubElement(profile, "gateways")

    for trunk in trunks:
        if not trunk.is_active:
            continue
        tenant = tenants.get(str(trunk.tenant_id))
        if not tenant:
            continue

        gw_name = f"{tenant.slug}-{trunk.name.lower().replace(' ', '-')}"
        gw = SubElement(gateways, "gateway", name=gw_name)
        _param(gw, "realm", trunk.host)
        _param(gw, "proxy", f"{trunk.host}:{trunk.port}")
        _param(gw, "register", "true" if trunk.auth_type == "registration" else "false")

        if trunk.username:
            _param(gw, "username", trunk.username)
        pwd = passwords.get(str(trunk.id), "")
        if pwd:
            _param(gw, "password", pwd)

        _param(gw, "caller-id-in-from", "true")
        _param(gw, "register-transport", trunk.transport)

    return _xml_to_string(doc)


def build_callcenter_config(
    tenants: list[Tenant],
    queues_by_tenant: dict[str, list[Queue]],
    extensions_by_tenant: dict[str, list[Extension]],
    prompt_map: dict[str, AudioPrompt] | None = None,
) -> str:
    """Generate callcenter.conf XML for all tenants' queues, agents, and tiers.

    Args:
        tenants: All active tenants.
        queues_by_tenant: Map of tenant_id → list of queues (with members loaded).
        extensions_by_tenant: Map of tenant_id → list of extensions.
        prompt_map: Map of prompt_id → AudioPrompt (for MOH paths).
    """
    prompt_map = prompt_map or {}

    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="configuration")
    config = SubElement(section, "configuration", name="callcenter.conf", description="CallCenter")
    queues_el = SubElement(config, "queues")
    agents_el = SubElement(config, "agents")
    tiers_el = SubElement(config, "tiers")

    # Track agents we've already emitted (agent names are global in FS)
    seen_agents: set[str] = set()

    for tenant in tenants:
        tid = str(tenant.id)
        domain_name = tenant.sip_domain or f"{tenant.slug}.sip.local"
        context_name = tenant.slug
        ext_map = {str(e.id): e for e in extensions_by_tenant.get(tid, [])}

        for q in queues_by_tenant.get(tid, []):
            if not q.is_active or not q.enabled:
                continue

            queue_fs_name = f"{context_name}-{q.name.lower().replace(' ', '-')}"
            queue_el = SubElement(queues_el, "queue", name=queue_fs_name)

            _param(queue_el, "strategy", q.strategy)
            _param(queue_el, "max-wait-time", str(q.max_wait_time))
            _param(queue_el, "max-wait-time-with-no-agent", str(q.max_wait_time_with_no_agent))
            _param(queue_el, "tier-rules-apply", str(q.tier_rules_apply).lower())
            _param(queue_el, "tier-rule-wait-second", str(q.tier_rule_wait_second))
            _param(
                queue_el,
                "tier-rule-wait-multiply-level",
                str(q.tier_rule_wait_multiply_level).lower(),
            )
            _param(
                queue_el, "tier-rule-no-agent-no-wait", str(q.tier_rule_no_agent_no_wait).lower()
            )
            _param(queue_el, "discard-abandoned-after", str(q.discard_abandoned_after))
            _param(queue_el, "abandoned-resume-allowed", str(q.abandoned_resume_allowed).lower())
            _param(queue_el, "time-base-score", "queue")
            _param(queue_el, "ring-progressively-delay", "10")

            if q.caller_exit_key:
                _param(queue_el, "caller-exit-keys", q.caller_exit_key)
            if q.wrapup_time:
                _param(queue_el, "agent-no-answer-status", "On Break")

            # MOH
            if q.moh_prompt_id:
                prompt = prompt_map.get(str(q.moh_prompt_id))
                if prompt and prompt.local_path:
                    _param(queue_el, "moh-sound", prompt.local_path)
                else:
                    _param(queue_el, "moh-sound", "local_stream://moh")
            else:
                _param(queue_el, "moh-sound", "local_stream://moh")

            # Process members → agents + tiers
            for member in q.members:
                ext = ext_map.get(str(member.extension_id))
                if not ext or not ext.is_active:
                    continue

                agent_name = f"{ext.extension_number}@{domain_name}"
                agent_status = ext.agent_status or "Available"

                # Only emit agent once (may be in multiple queues)
                if agent_name not in seen_agents:
                    seen_agents.add(agent_name)
                    agent_el = SubElement(agents_el, "agent")
                    agent_el.set("name", agent_name)
                    agent_el.set("type", "callback")
                    agent_el.set(
                        "contact",
                        f"[leg_timeout={q.ring_timeout}]user/{ext.extension_number}@{domain_name}",
                    )
                    agent_el.set("status", agent_status)
                    agent_el.set("no-answer-delay-time", "10")
                    if q.wrapup_time:
                        agent_el.set("wrap-up-time", str(q.wrapup_time))

                # Always emit tier (agent ↔ queue mapping)
                tier_el = SubElement(tiers_el, "tier")
                tier_el.set("agent", agent_name)
                tier_el.set("queue", queue_fs_name)
                tier_el.set("level", str(member.level))
                tier_el.set("position", str(member.position))

    return _xml_to_string(doc)


def build_conference_config() -> str:
    """Generate conference.conf XML with default profile and caller controls.

    This is returned to FreeSWITCH via mod_xml_curl configuration binding.
    """
    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="configuration")
    config = SubElement(section, "configuration", name="conference.conf", description="Conference")

    # Caller controls
    controls = SubElement(config, "caller-controls")
    group = SubElement(controls, "group", name="default")
    SubElement(group, "control", action="mute", digits="0")
    SubElement(group, "control", action="deaf mute", digits="*")
    SubElement(group, "control", action="hangup", digits="#")
    SubElement(group, "control", action="vol talk up", digits="3")
    SubElement(group, "control", action="vol talk dn", digits="1")
    SubElement(group, "control", action="vol listen up", digits="6")
    SubElement(group, "control", action="vol listen dn", digits="4")

    # Default profile
    profiles = SubElement(config, "profiles")
    profile = SubElement(profiles, "profile", name="default")
    _param(profile, "rate", "16000")
    _param(profile, "interval", "20")
    _param(profile, "energy-level", "100")
    _param(profile, "caller-controls", "default")
    _param(profile, "moh-sound", "local_stream://moh")
    _param(profile, "comfort-noise", "true")
    _param(profile, "enter-sound", "tone_stream://%(200,0,500,600,700)")
    _param(profile, "exit-sound", "tone_stream://%(500,0,300,200,100,50,25)")

    return _xml_to_string(doc)


# ── Helpers ──────────────────────────────────────────────────────────────


def _param(parent: Element, name: str, value: str) -> Element:
    return SubElement(parent, "param", name=name, value=value)


def _var(parent: Element, name: str, value: str) -> Element:
    return SubElement(parent, "variable", name=name, value=value)


def _action(parent: Element, application: str, data: str = "") -> Element:
    return SubElement(parent, "action", application=application, data=data)


def _condition(parent: Element, field: str, expression: str) -> Element:
    return SubElement(parent, "condition", field=field, expression=expression)


def _xml_to_string(element: Element) -> str:
    raw = tostring(element, encoding="unicode", xml_declaration=False)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{raw}'


def _toll_allow(class_of_service: str) -> str:
    mapping = {
        "international": "domestic,international,local,emergency",
        "domestic": "domestic,local,emergency",
        "local": "local,emergency",
        "internal": "emergency",
        "emergency_only": "emergency",
    }
    return mapping.get(class_of_service, "emergency")


def _get_vm_password(voicemail_box: VoicemailBox | None) -> str:
    if not voicemail_box:
        return ""
    # Return empty string; actual PIN auth is handled by encrypted_pin
    return ""


def _add_recording_actions(cond: Element, ext: Extension) -> None:
    """Add call recording actions based on extension recording policy."""
    recording_policy = getattr(ext, "recording_policy", "never")
    if recording_policy == "always":
        _action(
            cond,
            "export",
            "nolocal:execute_on_answer=record_session /recordings/${accountcode}/${uuid}.wav",
        )
    elif recording_policy == "on_demand":
        _action(
            cond,
            "bind_meta_app",
            "1 b s record_session::/recordings/${accountcode}/${uuid}.wav",
        )


def _add_feature_codes(context: Element, domain_name: str, vm_map: dict, extensions: list) -> None:
    """Add feature code extensions to dialplan context."""
    # *97 — Check voicemail (own mailbox)
    ext = SubElement(context, "extension", name="check-voicemail")
    _condition(ext, "destination_number", r"^\*97$")
    cond = ext.find("condition")
    _action(cond, "answer")
    _action(cond, "voicemail", f"check default {domain_name} ${{caller_id_number}}")

    # *78 — DND on
    ext = SubElement(context, "extension", name="dnd-on")
    _condition(ext, "destination_number", r"^\*78$")
    cond = ext.find("condition")
    _action(cond, "db", "insert/dnd/${caller_id_number}/true")
    _action(cond, "playback", "ivr/ivr-call_forward_set.wav")
    _action(cond, "hangup")

    # *79 — DND off
    ext = SubElement(context, "extension", name="dnd-off")
    _condition(ext, "destination_number", r"^\*79$")
    cond = ext.find("condition")
    _action(cond, "db", "delete/dnd/${caller_id_number}")
    _action(cond, "playback", "ivr/ivr-call_forward_cancel.wav")
    _action(cond, "hangup")

    # *72 — Call forward unconditional on (next arg is destination)
    ext = SubElement(context, "extension", name="cf-on")
    _condition(ext, "destination_number", r"^\*72(.+)$")
    cond = ext.find("condition")
    _action(cond, "db", "insert/cf/${caller_id_number}/$1")
    _action(cond, "playback", "ivr/ivr-call_forward_set.wav")
    _action(cond, "hangup")

    # *73 — Call forward unconditional off
    ext = SubElement(context, "extension", name="cf-off")
    _condition(ext, "destination_number", r"^\*73$")
    cond = ext.find("condition")
    _action(cond, "db", "delete/cf/${caller_id_number}")
    _action(cond, "playback", "ivr/ivr-call_forward_cancel.wav")
    _action(cond, "hangup")

    # *50 — Agent login (set Available)
    ext = SubElement(context, "extension", name="agent-login")
    _condition(ext, "destination_number", r"^\*50$")
    cond = ext.find("condition")
    _action(
        cond,
        "callcenter_config",
        f"agent set status ${{caller_id_number}}@{domain_name} 'Available'",
    )
    _action(cond, "playback", "ivr/ivr-you_are_now_logged_in.wav")
    _action(cond, "hangup")

    # *51 — Agent logout (set Logged Out)
    ext = SubElement(context, "extension", name="agent-logout")
    _condition(ext, "destination_number", r"^\*51$")
    cond = ext.find("condition")
    _action(
        cond,
        "callcenter_config",
        f"agent set status ${{caller_id_number}}@{domain_name} 'Logged Out'",
    )
    _action(cond, "playback", "ivr/ivr-you_are_now_logged_out.wav")
    _action(cond, "hangup")

    # *52 — Agent break toggle (set On Break)
    ext = SubElement(context, "extension", name="agent-break")
    _condition(ext, "destination_number", r"^\*52$")
    cond = ext.find("condition")
    _action(
        cond,
        "callcenter_config",
        f"agent set status ${{caller_id_number}}@{domain_name} 'On Break'",
    )
    _action(cond, "playback", "tone_stream://%(200,0,500,600,700)")
    _action(cond, "hangup")

    # *80[ext] — Direct intercom to single extension
    ext = SubElement(context, "extension", name="intercom")
    _condition(ext, "destination_number", r"^\*80(.+)$")
    cond = ext.find("condition")
    _action(cond, "export", "sip_auto_answer=true")
    _action(cond, "export", "sip_h_Call-Info=<sip:>;answer-after=0")
    _action(cond, "bridge", f"user/$1@{domain_name}")

    # *8 — Group pickup (pick up ringing call in same pickup group)
    ext = SubElement(context, "extension", name="group-pickup")
    _condition(ext, "destination_number", r"^\*8$")
    cond = ext.find("condition")
    _action(cond, "pickup", f"${{pickup_group}}@{domain_name}")

    # *90[dest] — Call forward busy on
    ext = SubElement(context, "extension", name="cfb-on")
    _condition(ext, "destination_number", r"^\*90(.+)$")
    cond = ext.find("condition")
    _action(cond, "db", "insert/cfb/${caller_id_number}/$1")
    _action(cond, "playback", "ivr/ivr-call_forward_set.wav")
    _action(cond, "hangup")

    # *91 — Call forward busy off
    ext = SubElement(context, "extension", name="cfb-off")
    _condition(ext, "destination_number", r"^\*91$")
    cond = ext.find("condition")
    _action(cond, "db", "delete/cfb/${caller_id_number}")
    _action(cond, "playback", "ivr/ivr-call_forward_cancel.wav")
    _action(cond, "hangup")

    # *92[dest] — Call forward no-answer on
    ext = SubElement(context, "extension", name="cfna-on")
    _condition(ext, "destination_number", r"^\*92(.+)$")
    cond = ext.find("condition")
    _action(cond, "db", "insert/cfna/${caller_id_number}/$1")
    _action(cond, "playback", "ivr/ivr-call_forward_set.wav")
    _action(cond, "hangup")

    # *93 — Call forward no-answer off
    ext = SubElement(context, "extension", name="cfna-off")
    _condition(ext, "destination_number", r"^\*93$")
    cond = ext.find("condition")
    _action(cond, "db", "delete/cfna/${caller_id_number}")
    _action(cond, "playback", "ivr/ivr-call_forward_cancel.wav")
    _action(cond, "hangup")

    # **[ext] — Directed pickup (pick up specific ringing extension)
    ext = SubElement(context, "extension", name="directed-pickup")
    _condition(ext, "destination_number", r"^\*\*(.+)$")
    cond = ext.find("condition")
    _action(cond, "set", "intercept_unanswered_only=true")
    _action(cond, "intercept", f"${{hash(select/{domain_name}-call_return/$1)}}")


def _add_parking_feature_codes(context: Element, domain_name: str, parking_lots: list) -> None:
    """Add *85 (valet park) and *86XX (valet retrieve) feature codes."""
    if not parking_lots:
        return

    # *85 — Park current call (auto-assign slot)
    ext = SubElement(context, "extension", name="valet-park")
    _condition(ext, "destination_number", r"^\*85$")
    cond = ext.find("condition")
    _action(cond, "answer")
    _action(cond, "valet_park", f"valet_parking@{domain_name} auto in")

    # *86[slot] — Retrieve parked call by slot number
    ext = SubElement(context, "extension", name="valet-retrieve")
    _condition(ext, "destination_number", r"^\*86(\d+)$")
    cond = ext.find("condition")
    _action(cond, "answer")
    _action(cond, "valet_park", f"valet_parking@{domain_name} $1 out")


def _add_parking_slot_retrieval(context: Element, domain_name: str, parking_lots: list) -> None:
    """Add direct-dial slot number retrieval for each parking lot's slot range."""
    for lot in parking_lots:
        if lot.slot_start == lot.slot_end:
            # Single slot — exact match
            regex = f"^{lot.slot_start}$"
        else:
            # Build regex matching the slot range
            regex = _slot_range_regex(lot.slot_start, lot.slot_end)

        ext = SubElement(context, "extension", name=f"park-retrieve-lot-{lot.lot_number}")
        _condition(ext, "destination_number", regex)
        cond = ext.find("condition")
        _action(cond, "answer")
        _action(
            cond,
            "valet_park",
            f"valet_parking@{domain_name} ${{destination_number}} out",
        )


def _slot_range_regex(start: int, end: int) -> str:
    """Build a regex that matches integer range [start, end].

    For small ranges (≤20 slots) uses alternation: ^(70|71|72|...|79)$
    For larger ranges, falls back to broad numeric match — FreeSWITCH valet_park
    will return an error for out-of-range slots anyway.
    """
    count = end - start + 1
    if count <= 20:
        alternatives = "|".join(str(n) for n in range(start, end + 1))
        return f"^({alternatives})$"
    # Broad match — let FS handle out-of-range
    digit_count = len(str(end))
    return f"^\\d{{{digit_count}}}$"


def _add_follow_me_bridges(
    cond: Element,
    fm,
    ext_number_map: dict,
    domain_name: str,
    context_name: str,
) -> None:
    """Add follow-me bridge actions after primary extension bridge."""
    destinations = sorted(fm.destinations, key=lambda d: d.position)
    if not destinations:
        return

    def _dest_bridge_str(dest_number: str) -> str:
        """Build bridge string for a follow-me destination."""
        # Check if destination is an internal extension number
        if dest_number in ext_number_map:
            return f"user/{dest_number}@{domain_name}"
        # External number — use loopback to re-enter dialplan for outbound routing
        return f"loopback/{dest_number}/{context_name}"

    if fm.strategy == "ring_all_external":
        # Ring all external destinations simultaneously
        parts = [_dest_bridge_str(d.destination) for d in destinations]
        _action(cond, "bridge", ",".join(parts))
    else:
        # Sequential: try each destination in order
        for dest in destinations:
            _action(cond, "set", f"call_timeout={dest.ring_time}")
            _action(cond, "bridge", _dest_bridge_str(dest.destination))


def _ring_group_bridge_string(
    rg: RingGroup, ext_map: dict[str, Extension], domain_name: str
) -> str:
    """Build bridge string for a ring group based on strategy."""
    active_members = []
    for member in sorted(rg.members, key=lambda m: m.position):
        ext = ext_map.get(str(member.extension_id))
        if ext and ext.is_active:
            active_members.append(ext)

    if not active_members:
        return ""

    if rg.ring_strategy == "simultaneous":
        # Comma-separated = ring all at once
        parts = [f"user/{e.extension_number}@{domain_name}" for e in active_members]
        return ",".join(parts)
    elif rg.ring_strategy == "sequential":
        # Pipe-separated = try one at a time
        parts = [f"user/{e.extension_number}@{domain_name}" for e in active_members]
        return "|".join(parts)
    else:
        # Default to simultaneous for unsupported strategies
        parts = [f"user/{e.extension_number}@{domain_name}" for e in active_members]
        return ",".join(parts)


def _add_inbound_destination(
    cond: Element,
    route,
    ext_map: dict,
    vm_map: dict,
    rg_map: dict,
    domain_name: str,
    context_name: str = "",
    ivr_map: dict | None = None,
    queue_map: dict | None = None,
    conference_map: dict | None = None,
) -> None:
    """Add actions for an inbound route's destination."""
    if route.destination_type == "extension" and route.destination_id:
        dest_ext = ext_map.get(str(route.destination_id))
        if dest_ext:
            _action(cond, "set", f"call_timeout={dest_ext.call_forward_ring_time}")
            _action(cond, "set", "hangup_after_bridge=true")
            _action(cond, "set", "continue_on_fail=true")
            _action(cond, "bridge", f"user/{dest_ext.extension_number}@{domain_name}")
            # Fallback to voicemail
            if dest_ext.voicemail_box_id:
                vm = vm_map.get(str(dest_ext.voicemail_box_id))
                if vm and vm.is_active:
                    _action(cond, "answer")
                    _action(cond, "voicemail", f"default {domain_name} {vm.mailbox_number}")

    elif route.destination_type == "ring_group" and route.destination_id:
        rg = rg_map.get(str(route.destination_id))
        if rg:
            _action(cond, "set", f"call_timeout={rg.ring_time}")
            _action(cond, "set", "hangup_after_bridge=true")
            _action(cond, "set", "continue_on_fail=true")
            bridge = _ring_group_bridge_string(rg, ext_map, domain_name)
            if bridge:
                _action(cond, "bridge", bridge)

    elif route.destination_type == "voicemail" and route.destination_id:
        vm = vm_map.get(str(route.destination_id))
        if vm:
            _action(cond, "answer")
            _action(cond, "voicemail", f"default {domain_name} {vm.mailbox_number}")

    elif route.destination_type == "ivr" and route.destination_id:
        # Route to IVR menu
        _action(cond, "answer")
        ivr_name = f"{context_name}-ivr-{route.destination_id}"
        if ivr_map:
            ivr = ivr_map.get(str(route.destination_id))
            if ivr:
                ivr_name = f"{context_name}-ivr-{ivr.name.lower().replace(' ', '-')}"
        _action(cond, "ivr", ivr_name)

    elif route.destination_type == "time_condition" and route.destination_id:
        # Route to time condition (transfer to tc-* extension in same context)
        _action(cond, "transfer", f"tc-{route.destination_id} XML {context_name}")

    elif route.destination_type == "queue" and route.destination_id:
        queue = (queue_map or {}).get(str(route.destination_id))
        if queue:
            queue_fs_name = f"{context_name}-{queue.name.lower().replace(' ', '-')}"
            _action(cond, "set", "hangup_after_bridge=true")
            _action(cond, "set", "continue_on_fail=true")
            _action(cond, "callcenter", queue_fs_name)

    elif route.destination_type == "conference" and route.destination_id:
        cb = (conference_map or {}).get(str(route.destination_id))
        if cb:
            conf_name = f"{context_name}-conf-{cb.room_number}"
            _action(cond, "answer")
            flags = ["waste"]
            if cb.wait_for_moderator:
                flags.append("waitmod")
            if cb.muted_on_join:
                flags.append("mute")
            flag_str = "|".join(flags)
            _action(cond, "conference", f"{conf_name}@default+flags{{{flag_str}}}")

    elif route.destination_type == "ai_agent" and route.destination_id:
        # AI voice agent — stream audio via mod_audio_fork to AI engine
        context_id = str(route.destination_id)
        _action(cond, "answer", "")
        _action(cond, "set", f"ai_agent_context={context_id}")
        _action(cond, "set", f"ai_agent_tenant={route.tenant_id!s}")
        _action(cond, "audio_fork", "ws://ai-engine:8090/audio/${uuid} mono 8000")

    elif route.destination_type == "terminate":
        _action(cond, "hangup", "NORMAL_CLEARING")


def _dial_pattern_to_regex(pattern: str) -> str:
    """Convert FreePBX-style dial pattern to regex.

    Pattern characters:
        X = [0-9]
        Z = [1-9]
        N = [2-9]
        . = .+ (one or more of anything)
        | = literal (no special meaning, just pass through)
        All other chars are literal.
    """
    regex = "^"
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "X":
            regex += "[0-9]"
        elif c == "Z":
            regex += "[1-9]"
        elif c == "N":
            regex += "[2-9]"
        elif c == ".":
            regex += ".+"
        elif c in r"()[]{}+*?\\^$":
            regex += "\\" + c
        else:
            regex += c
        i += 1
    regex += "$"
    return regex


def _outbound_trunk_bridge(
    route: OutboundRoute, trunk_map: dict[str, SIPTrunk], tenant: Tenant
) -> str:
    """Build bridge string for outbound routing through trunk(s)."""
    parts = []
    for assignment in sorted(route.trunk_assignments, key=lambda a: a.position):
        trunk = trunk_map.get(str(assignment.trunk_id))
        if not trunk or not trunk.is_active:
            continue
        gw_name = f"{tenant.slug}-{trunk.name.lower().replace(' ', '-')}"
        parts.append(f"sofia/gateway/{gw_name}/${{dialed_number}}")

    # Pipe-separated for failover
    return "|".join(parts)


def _add_security_feature_codes(context: Element, domain_name: str, security_config) -> None:
    """Add security feature codes to dialplan context."""
    if not security_config or not security_config.is_active:
        return

    if security_config.panic_enabled:
        panic_code = security_config.panic_feature_code or "*0911"
        # Escape the * for regex
        escaped_code = re.escape(panic_code)

        # Panic button — sets channel variable for ESL event listener detection
        ext = SubElement(context, "extension", name="panic-alert")
        _condition(ext, "destination_number", f"^{escaped_code}$")
        cond = ext.find("condition")
        _action(cond, "answer")
        _action(cond, "set", "panic_alert=true")
        _action(cond, "set", "panic_tenant_slug=${accountcode}")
        _action(cond, "playback", "tone_stream://%(500,0,1400);%(500,0,1400);%(500,0,1400)")
        _action(cond, "hangup")

    allcall_code = security_config.emergency_allcall_code or "*0999"
    escaped_allcall = re.escape(allcall_code)

    # Emergency all-call — pages all emergency paging zone members
    ext = SubElement(context, "extension", name="emergency-allcall")
    _condition(ext, "destination_number", f"^{escaped_allcall}$")
    cond = ext.find("condition")
    _action(cond, "answer")
    _action(cond, "set", "conference_auto_outcall_timeout=60")
    _action(cond, "set", "sip_auto_answer=true")
    _action(cond, "set", "sip_h_Call-Info=<sip:>;answer-after=0")
    _action(
        cond,
        "conference",
        f"emergency-allcall-{domain_name.replace('.', '-')}@default+flags{{mute}}",
    )


def _add_paging_zone_extensions(
    context: Element, domain_name: str, context_name: str, paging_zones
) -> None:
    """Add paging zone extensions to dialplan context."""
    if not paging_zones:
        return

    for zone in paging_zones:
        if not zone.is_active:
            continue
        zone_conf_name = f"{context_name}-paging-zone-{zone.zone_number}"
        dp_ext = SubElement(context, "extension", name=f"paging-zone-{zone.zone_number}")
        _condition(dp_ext, "destination_number", f"^{re.escape(zone.zone_number)}$")
        cond = dp_ext.find("condition")
        _action(cond, "answer")
        _action(cond, "set", "conference_auto_outcall_timeout=60")

        # Auto-outcall to all zone members
        if hasattr(zone, "members") and zone.members:
            for member in sorted(zone.members, key=lambda m: m.position):
                _action(
                    cond,
                    "conference_set_auto_outcall",
                    f"user/{member.extension_id}@{domain_name}",
                )

        _action(cond, "set", "sip_auto_answer=true")
        _action(cond, "set", "sip_h_Call-Info=<sip:>;answer-after=0")
        flags = "mute" if not zone.is_emergency else "mute|endconf"
        _action(cond, "conference", f"{zone_conf_name}@default+flags{{{flags}}}")


def _add_camp_on_feature_codes(
    context: Element, domain_name: str, context_name: str, camp_on_config
) -> None:
    """Add camp-on feature code and handler extension to dialplan context."""
    if not camp_on_config or not camp_on_config.enabled or not camp_on_config.is_active:
        return

    fc = re.escape(camp_on_config.feature_code)

    # Feature code: *88[ext] — explicit camp-on request via feature code
    dp_ext = SubElement(context, "extension", name="camp-on-feature")
    _condition(dp_ext, "destination_number", f"^{fc}(\\d+)$")
    cond = dp_ext.find("condition")
    _action(cond, "answer")
    _action(cond, "set", "campon_target=$1")
    _action(
        cond,
        "curl",
        "http://api:8000/internal/camp-on/create "
        "post tenant_slug=${accountcode}"
        "&caller_extension_number=${caller_id_number}"
        "&target_extension_number=$1"
        "&reason=busy"
        "&original_call_id=${uuid}",
    )
    _action(cond, "playback", "ivr/ivr-you_will_be_notified.wav")
    _action(cond, "hangup")

    # Handler: camp-on-handler-1 — called by execute_extension after DTMF "1"
    dp_ext = SubElement(context, "extension", name="camp-on-handler-1")
    _condition(dp_ext, "destination_number", "^camp-on-handler-1$")
    cond = dp_ext.find("condition")
    _action(
        cond,
        "curl",
        "http://api:8000/internal/camp-on/create "
        "post tenant_slug=${accountcode}"
        "&caller_extension_number=${caller_id_number}"
        "&target_extension_number=${dialed_extension}"
        "&reason=${originate_disposition}"
        "&original_call_id=${uuid}",
    )
    _action(cond, "playback", "ivr/ivr-you_will_be_notified.wav")
    _action(cond, "hangup")


def _anti_action(parent: Element, application: str, data: str = "") -> Element:
    """Add an anti-action element (executes when condition does NOT match)."""
    return SubElement(parent, "anti-action", application=application, data=data)


def _add_time_condition_extension(
    context: Element,
    tc,
    ext_map: dict,
    vm_map: dict,
    rg_map: dict,
    domain_name: str,
    context_name: str,
    ivr_map: dict | None = None,
    queue_map: dict | None = None,
    conference_map: dict | None = None,
) -> None:
    """Add a time condition extension to the dialplan with FS native time matching.

    Handles manual override (force day/night) and holiday calendar preemption.
    """
    dest_kwargs = dict(
        ext_map=ext_map,
        vm_map=vm_map,
        rg_map=rg_map,
        domain_name=domain_name,
        context_name=context_name,
        ivr_map=ivr_map,
        queue_map=queue_map,
        conference_map=conference_map,
    )

    # Manual override: if set, route unconditionally (skip time rules and holidays)
    manual_override = getattr(tc, "manual_override", None)
    if manual_override == "day":
        dp_ext = SubElement(context, "extension", name=f"tc-{tc.id}")
        _condition(dp_ext, "destination_number", f"^tc-{re.escape(str(tc.id))}$")
        dest_cond = dp_ext.find("condition")
        _add_destination_actions(
            dest_cond,
            tc.match_destination_type,
            tc.match_destination_id,
            use_action=True,
            **dest_kwargs,
        )
        return
    elif manual_override == "night":
        dp_ext = SubElement(context, "extension", name=f"tc-{tc.id}")
        _condition(dp_ext, "destination_number", f"^tc-{re.escape(str(tc.id))}$")
        dest_cond = dp_ext.find("condition")
        _add_destination_actions(
            dest_cond,
            tc.nomatch_destination_type,
            tc.nomatch_destination_id,
            use_action=True,
            **dest_kwargs,
        )
        return

    # Holiday preemption: add holiday check extensions BEFORE the main TC extension
    holiday_calendar = getattr(tc, "holiday_calendar", None)
    if holiday_calendar and getattr(holiday_calendar, "is_active", False):
        entries = getattr(holiday_calendar, "entries", []) or []
        for entry in entries:
            holiday_ext = SubElement(context, "extension", name=f"tc-{tc.id}-holiday-{entry.id}")
            dest_cond = _condition(
                holiday_ext, "destination_number", f"^tc-{re.escape(str(tc.id))}$"
            )

            # Date-matching condition
            date_attrs = {"mon": str(entry.date.month), "mday": str(entry.date.day)}
            if not entry.recur_annually:
                date_attrs["year"] = str(entry.date.year)
            if not entry.all_day and entry.start_time and entry.end_time:
                date_attrs["time-of-day"] = (
                    f"{entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')}"
                )
            date_cond = SubElement(holiday_ext, "condition", **date_attrs)

            # Route to no-match (after-hours/holiday) destination
            _add_destination_actions(
                date_cond,
                tc.nomatch_destination_type,
                tc.nomatch_destination_id,
                use_action=True,
                **dest_kwargs,
            )

    # Main TC extension
    dp_ext = SubElement(context, "extension", name=f"tc-{tc.id}")

    # First condition: match the destination_number for this TC
    _condition(dp_ext, "destination_number", f"^tc-{re.escape(str(tc.id))}$")
    dest_cond = dp_ext.find("condition")
    _action(dest_cond, "set", "continue_on_fail=true")

    # Build time condition using FS native matching
    wday = None
    tod = None
    for rule in tc.rules or []:
        rule_type = rule.get("type", "")
        if rule_type == "day_of_week":
            days = rule.get("days", [])
            if days:
                wday = "-".join(str(d) for d in sorted(days))
        elif rule_type == "time_of_day":
            start = rule.get("start_time", "00:00")
            end = rule.get("end_time", "23:59")
            tod = f"{start}-{end}"

    # Create the time-matching condition
    tc_cond_attrs = {}
    if wday:
        tc_cond_attrs["wday"] = wday
    if tod:
        tc_cond_attrs["time-of-day"] = tod

    if tc_cond_attrs:
        time_cond = SubElement(dp_ext, "condition", **tc_cond_attrs)

        # Match actions
        _add_destination_actions(
            time_cond,
            tc.match_destination_type,
            tc.match_destination_id,
            use_action=True,
            **dest_kwargs,
        )

        # No-match (anti-actions)
        _add_destination_actions(
            time_cond,
            tc.nomatch_destination_type,
            tc.nomatch_destination_id,
            use_action=False,
            **dest_kwargs,
        )
    else:
        # No time rules — always route to match destination
        _add_destination_actions(
            dest_cond,
            tc.match_destination_type,
            tc.match_destination_id,
            use_action=True,
            **dest_kwargs,
        )


def _add_destination_actions(
    cond: Element,
    dest_type: str,
    dest_id,
    ext_map: dict,
    vm_map: dict,
    rg_map: dict,
    domain_name: str,
    context_name: str,
    ivr_map: dict | None,
    queue_map: dict | None = None,
    conference_map: dict | None = None,
    use_action: bool = True,
) -> None:
    """Add action or anti-action elements for a destination type."""
    add_fn = _action if use_action else _anti_action
    dest_id_str = str(dest_id) if dest_id else None

    if dest_type == "extension" and dest_id_str:
        ext = ext_map.get(dest_id_str)
        if ext:
            add_fn(cond, "transfer", f"{ext.extension_number} XML {context_name}")

    elif dest_type == "ring_group" and dest_id_str:
        rg = rg_map.get(dest_id_str)
        if rg:
            add_fn(cond, "transfer", f"{rg.group_number} XML {context_name}")

    elif dest_type == "voicemail" and dest_id_str:
        vm = vm_map.get(dest_id_str)
        if vm:
            add_fn(cond, "answer", "")
            add_fn(cond, "voicemail", f"default {domain_name} {vm.mailbox_number}")

    elif dest_type == "ivr" and dest_id_str:
        ivr_name = f"{context_name}-ivr-{dest_id_str}"
        if ivr_map:
            ivr = ivr_map.get(dest_id_str)
            if ivr:
                ivr_name = f"{context_name}-ivr-{ivr.name.lower().replace(' ', '-')}"
        add_fn(cond, "answer", "")
        add_fn(cond, "ivr", ivr_name)

    elif dest_type == "queue" and dest_id_str:
        queue = (queue_map or {}).get(dest_id_str)
        if queue:
            queue_fs_name = f"{context_name}-{queue.name.lower().replace(' ', '-')}"
            add_fn(cond, "callcenter", queue_fs_name)

    elif dest_type == "conference" and dest_id_str:
        cb = (conference_map or {}).get(dest_id_str)
        if cb:
            conf_name = f"{context_name}-conf-{cb.room_number}"
            add_fn(cond, "answer", "")
            flags = ["waste"]
            if cb.wait_for_moderator:
                flags.append("waitmod")
            if cb.muted_on_join:
                flags.append("mute")
            flag_str = "|".join(flags)
            add_fn(cond, "conference", f"{conf_name}@default+flags{{{flag_str}}}")

    elif dest_type == "hangup" or dest_type == "terminate":
        add_fn(cond, "hangup", "NORMAL_CLEARING")


def build_ivr_config(
    tenant: Tenant,
    ivr_menus: list[IVRMenu],
    prompt_map: dict[str, AudioPrompt] | None = None,
) -> str:
    """Generate ivr.conf XML for all IVR menus in a tenant.

    This is returned to FreeSWITCH via mod_xml_curl configuration binding.
    """
    domain_name = tenant.sip_domain or f"{tenant.slug}.sip.local"
    context_name = tenant.slug
    prompt_map = prompt_map or {}

    doc = Element("document", type="freeswitch/xml")
    section = SubElement(doc, "section", name="configuration")
    config = SubElement(section, "configuration", name="ivr.conf", description="IVR menus")
    menus = SubElement(config, "menus")

    for ivr in ivr_menus:
        if not ivr.is_active or not ivr.enabled:
            continue

        menu_name = f"{context_name}-ivr-{ivr.name.lower().replace(' ', '-')}"
        menu_attrs = {"name": menu_name}

        # Prompt paths
        if ivr.greet_long_prompt_id:
            prompt = prompt_map.get(str(ivr.greet_long_prompt_id))
            if prompt and prompt.local_path:
                menu_attrs["greet-long"] = prompt.local_path
        if ivr.greet_short_prompt_id:
            prompt = prompt_map.get(str(ivr.greet_short_prompt_id))
            if prompt and prompt.local_path:
                menu_attrs["greet-short"] = prompt.local_path
        if ivr.invalid_sound_prompt_id:
            prompt = prompt_map.get(str(ivr.invalid_sound_prompt_id))
            if prompt and prompt.local_path:
                menu_attrs["invalid-sound"] = prompt.local_path
        if ivr.exit_sound_prompt_id:
            prompt = prompt_map.get(str(ivr.exit_sound_prompt_id))
            if prompt and prompt.local_path:
                menu_attrs["exit-sound"] = prompt.local_path

        menu_attrs["timeout"] = str(ivr.timeout * 1000)  # FS expects milliseconds
        menu_attrs["max-failures"] = str(ivr.max_failures)
        menu_attrs["max-timeouts"] = str(ivr.max_timeouts)
        menu_attrs["inter-digit-timeout"] = str(ivr.inter_digit_timeout * 1000)
        menu_attrs["digit-len"] = str(ivr.digit_len)

        menu_el = SubElement(menus, "menu", **menu_attrs)

        # Menu entries (options)
        for opt in sorted(ivr.options, key=lambda o: o.position):
            entry_action = _ivr_option_to_fs_action(opt, context_name, domain_name)
            if entry_action:
                SubElement(
                    menu_el, "entry", action="menu-exec-app", digits=opt.digits, param=entry_action
                )

    return _xml_to_string(doc)


def _ivr_option_to_fs_action(opt, context_name: str, domain_name: str) -> str:
    """Convert an IVR menu option to a FreeSWITCH action string."""
    if opt.action_type == "extension" and opt.action_target_value:
        return f"transfer {opt.action_target_value} XML {context_name}"
    elif opt.action_type == "extension" and opt.action_target_id:
        return f"transfer {opt.action_target_id} XML {context_name}"
    elif opt.action_type == "ring_group" and opt.action_target_value:
        return f"transfer {opt.action_target_value} XML {context_name}"
    elif opt.action_type == "voicemail" and opt.action_target_value:
        return f"transfer *{opt.action_target_value} XML {context_name}"
    elif opt.action_type == "ivr" and opt.action_target_value:
        return f"ivr {context_name}-ivr-{opt.action_target_value}"
    elif (
        opt.action_type in ("conference", "queue", "external_transfer") and opt.action_target_value
    ):
        return f"transfer {opt.action_target_value} XML {context_name}"
    elif opt.action_type == "hangup":
        return "hangup"
    elif opt.action_type == "repeat":
        return "menu-top"
    return ""


def _resolve_moh_path(
    moh_prompt_id, prompt_map: dict, tenant_default_path: str | None
) -> str | None:
    """Resolve MOH audio path from prompt ID or tenant default."""
    if moh_prompt_id:
        prompt = prompt_map.get(str(moh_prompt_id))
        if prompt and prompt.local_path:
            return prompt.local_path
    return tenant_default_path  # may be None → FS uses default local_stream://moh


def _cid_pattern_to_regex(pattern: str) -> str:
    """Convert a caller ID match pattern to a regex.

    Examples:
        "+1555*" → "^\\+?1555.*$"
        "anonymous" → "^(anonymous|Anonymous|unknown)$"
        "+1*" → "^\\+?1.*$"
    """
    if pattern.lower() in ("anonymous", "unknown", "unavailable"):
        return "^(anonymous|Anonymous|unknown|unavailable|Unavailable)$"

    regex = "^"
    for c in pattern:
        if c == "*":
            regex += ".*"
        elif c == "+":
            regex += "\\+?"
        elif c in r"()[]{}?\\^$.|":
            regex += "\\" + c
        else:
            regex += c
    regex += "$"
    return regex


def _add_blocklist_extensions(
    context: Element,
    rules: list,
    vm_map: dict,
    domain_name: str,
    context_name: str,
) -> None:
    """Add caller ID blocklist/allowlist extensions to dialplan.

    Rules are sorted by priority DESC (higher = evaluated first).
    Block rules use continue="false" to stop call processing.
    Allow rules use continue="true" to let calls proceed.
    """
    if not rules:
        return

    active_rules = [r for r in rules if r.is_active]
    sorted_rules = sorted(active_rules, key=lambda r: r.priority, reverse=True)

    for rule in sorted_rules:
        cid_regex = _cid_pattern_to_regex(rule.match_pattern)
        rule_action = rule.action

        # Determine if this extension should stop processing
        continue_val = "true" if rule_action == "allow" else "false"

        ext_el = SubElement(
            context,
            "extension",
            name=f"cid-rule-{rule.id}",
            **{"continue": continue_val},
        )
        cond = SubElement(ext_el, "condition", field="caller_id_number", expression=cid_regex)

        if rule_action == "reject":
            _action(cond, "respond", "486 Busy Here")
        elif rule_action == "hangup":
            _action(cond, "hangup")
        elif rule_action == "voicemail":
            if rule.destination_id:
                vm = vm_map.get(str(rule.destination_id))
                if vm:
                    _action(cond, "answer")
                    _action(cond, "voicemail", f"default {domain_name} {vm.mailbox_number}")
                else:
                    _action(cond, "respond", "486 Busy Here")
            else:
                _action(cond, "respond", "486 Busy Here")
        elif rule_action == "allow":
            _action(cond, "set", "caller_allowed=true")
