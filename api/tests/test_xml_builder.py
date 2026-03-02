"""Tests for FreeSWITCH XML builder — pure function unit tests."""

import uuid
from xml.etree.ElementTree import fromstring

import pytest

from new_phone.freeswitch.xml_builder import (
    _cid_pattern_to_regex,
    _dial_pattern_to_regex,
    _ring_group_bridge_string,
    _toll_allow,
    build_dialplan,
    build_directory_user,
    build_gateway_config,
    build_not_found,
)

# ── Fixtures / Helpers ──────────────────────────────────────────────


class FakeObj:
    """Simple attribute bag for test data."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_tenant(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "slug": "acme",
        "sip_domain": "acme.sip.local",
        "name": "Acme Corp",
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_extension(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "extension_number": "100",
        "sip_username": "b0000000-100",
        "sip_password_hash": "hashed",
        "encrypted_sip_password": "encrypted",
        "user_id": None,
        "voicemail_box_id": None,
        "internal_cid_name": "Test User",
        "internal_cid_number": "100",
        "external_cid_name": None,
        "external_cid_number": None,
        "emergency_cid_number": None,
        "call_forward_unconditional": None,
        "call_forward_busy": None,
        "call_forward_no_answer": None,
        "call_forward_not_registered": None,
        "call_forward_ring_time": 25,
        "dnd_enabled": False,
        "call_waiting": True,
        "max_registrations": 3,
        "outbound_cid_mode": "internal",
        "class_of_service": "domestic",
        "recording_policy": "never",
        "pickup_group": None,
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_voicemail_box(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "mailbox_number": "100",
        "pin_hash": "hashed",
        "encrypted_pin": "encrypted",
        "greeting_type": "default",
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_trunk(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Test Trunk",
        "auth_type": "registration",
        "host": "sip.example.com",
        "port": 5061,
        "username": "trunk_user",
        "encrypted_password": "encrypted",
        "transport": "tls",
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_inbound_route(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Main Number",
        "did_id": None,
        "destination_type": "extension",
        "destination_id": None,
        "cid_name_prefix": None,
        "enabled": True,
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_outbound_route(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "US Domestic",
        "dial_pattern": "1NXXNXXXXXX",
        "prepend_digits": None,
        "strip_digits": 0,
        "cid_mode": "extension",
        "custom_cid": None,
        "priority": 100,
        "enabled": True,
        "is_active": True,
        "trunk_assignments": [],
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_ring_group(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "group_number": "*601",
        "name": "Sales Team",
        "ring_strategy": "simultaneous",
        "ring_time": 25,
        "ring_time_per_member": 15,
        "skip_busy": True,
        "cid_passthrough": True,
        "confirm_calls": False,
        "failover_dest_type": None,
        "failover_dest_id": None,
        "is_active": True,
        "members": [],
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_did(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "number": "+15551001000",
        "provider": "clearlyip",
        "status": "active",
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_rg_member(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "ring_group_id": uuid.uuid4(),
        "extension_id": uuid.uuid4(),
        "position": 0,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_trunk_assignment(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "outbound_route_id": uuid.uuid4(),
        "trunk_id": uuid.uuid4(),
        "position": 0,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


# ── Tests: build_not_found ──


def test_not_found_returns_xml():
    xml = build_not_found()
    assert '<?xml version="1.0"' in xml
    assert 'status="not found"' in xml
    root = fromstring(xml)
    assert root.tag == "document"


# ── Tests: build_directory_user ──


def test_directory_user_basic():
    tenant = make_tenant()
    ext = make_extension()
    xml = build_directory_user(ext, tenant, None, "secret123")
    root = fromstring(xml)

    assert root.attrib["type"] == "freeswitch/xml"

    domain = root.find(".//domain")
    assert domain is not None
    assert domain.attrib["name"] == "acme.sip.local"

    user = root.find(".//user")
    assert user is not None
    assert user.attrib["id"] == "100"

    # Password param
    params = {p.attrib["name"]: p.attrib["value"] for p in user.findall(".//param")}
    assert params["password"] == "secret123"
    assert params["max-registrations"] == "3"

    # Variables
    variables = {v.attrib["name"]: v.attrib["value"] for v in user.findall(".//variable")}
    assert variables["user_context"] == "acme"
    assert variables["toll_allow"] == "domestic,local,emergency"
    assert variables["effective_caller_id_name"] == "Test User"
    assert variables["accountcode"] == "acme"


def test_directory_user_with_voicemail():
    tenant = make_tenant()
    vm = make_voicemail_box(mailbox_number="100")
    ext = make_extension(voicemail_box_id=vm.id)
    xml = build_directory_user(ext, tenant, vm, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["mailbox"] == "100"


def test_directory_user_with_dnd():
    tenant = make_tenant()
    ext = make_extension(dnd_enabled=True)
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["do_not_disturb"] == "true"


def test_directory_user_with_call_forward():
    tenant = make_tenant()
    ext = make_extension(call_forward_unconditional="200")
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["forward_immediate"] == "200"


def test_directory_user_international_cos():
    tenant = make_tenant()
    ext = make_extension(class_of_service="international")
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["toll_allow"] == "domestic,international,local,emergency"


def test_directory_user_emergency_only_cos():
    tenant = make_tenant()
    ext = make_extension(class_of_service="emergency_only")
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["toll_allow"] == "emergency"


def test_directory_user_external_cid():
    tenant = make_tenant()
    ext = make_extension(
        external_cid_name="Acme Corp",
        external_cid_number="+15551001000",
    )
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["outbound_caller_id_name"] == "Acme Corp"
    assert variables["outbound_caller_id_number"] == "+15551001000"


def test_directory_user_fallback_sip_domain():
    """When tenant.sip_domain is None, fall back to slug.sip.local."""
    tenant = make_tenant(sip_domain=None)
    ext = make_extension()
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    domain = root.find(".//domain")
    assert domain.attrib["name"] == "acme.sip.local"


# ── Tests: build_dialplan ──


def test_dialplan_has_feature_codes():
    tenant = make_tenant()
    xml = build_dialplan(tenant, [], [], [], [], [], [], [])
    root = fromstring(xml)

    context = root.find(".//context")
    assert context.attrib["name"] == "acme"

    ext_names = [e.attrib["name"] for e in context.findall("extension")]
    assert "check-voicemail" in ext_names
    assert "dnd-on" in ext_names
    assert "dnd-off" in ext_names
    assert "cf-on" in ext_names
    assert "cf-off" in ext_names


def test_dialplan_local_extensions():
    tenant = make_tenant()
    ext = make_extension(extension_number="100")
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "local-100" in ext_names


def test_dialplan_extension_with_voicemail_fallback():
    tenant = make_tenant()
    vm = make_voicemail_box(mailbox_number="100")
    ext = make_extension(extension_number="100", voicemail_box_id=vm.id)
    xml = build_dialplan(tenant, [ext], [], [], [], [vm], [], [])
    root = fromstring(xml)

    # Find the local-100 extension
    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [a.attrib.get("application") for a in dp_ext.findall(".//action")]
            assert "voicemail" in actions
            break
    else:
        pytest.fail("local-100 extension not found")


def test_dialplan_dnd_extension():
    tenant = make_tenant()
    ext = make_extension(extension_number="100", dnd_enabled=True)
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [a.attrib.get("application") for a in dp_ext.findall(".//action")]
            assert "respond" in actions
            break


def test_dialplan_ring_group_simultaneous():
    tenant = make_tenant()
    ext1 = make_extension(extension_number="100")
    ext2 = make_extension(extension_number="101")

    member1 = make_rg_member(extension_id=ext1.id, position=0)
    member2 = make_rg_member(extension_id=ext2.id, position=1)
    rg = make_ring_group(
        group_number="*601",
        ring_strategy="simultaneous",
        members=[member1, member2],
    )

    xml = build_dialplan(tenant, [ext1, ext2], [], [], [rg], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "ring-group-*601":
            actions = {a.attrib.get("application"): a.attrib.get("data") for a in dp_ext.findall(".//action")}
            bridge = actions.get("bridge", "")
            # Simultaneous = comma-separated
            assert "," in bridge
            assert "user/100@acme.sip.local" in bridge
            assert "user/101@acme.sip.local" in bridge
            break
    else:
        pytest.fail("ring group extension not found")


def test_dialplan_ring_group_sequential():
    tenant = make_tenant()
    ext1 = make_extension(extension_number="100")
    ext2 = make_extension(extension_number="101")

    member1 = make_rg_member(extension_id=ext1.id, position=0)
    member2 = make_rg_member(extension_id=ext2.id, position=1)
    rg = make_ring_group(
        group_number="*601",
        ring_strategy="sequential",
        members=[member1, member2],
    )

    xml = build_dialplan(tenant, [ext1, ext2], [], [], [rg], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "ring-group-*601":
            actions = {a.attrib.get("application"): a.attrib.get("data") for a in dp_ext.findall(".//action")}
            bridge = actions.get("bridge", "")
            # Sequential = pipe-separated
            assert "|" in bridge
            break


def test_dialplan_inbound_route_to_extension():
    tenant = make_tenant()
    ext = make_extension(extension_number="100")
    did = make_did(number="+15551001000")
    route = make_inbound_route(
        did_id=did.id,
        destination_type="extension",
        destination_id=ext.id,
    )

    xml = build_dialplan(tenant, [ext], [route], [], [], [], [], [did])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "inbound-+15551001000" in ext_names


def test_dialplan_outbound_route_with_trunk():
    tenant = make_tenant()
    trunk = make_trunk(name="ClearlyIP", tenant_id=tenant.id)
    assignment = make_trunk_assignment(trunk_id=trunk.id, position=0)
    route = make_outbound_route(
        dial_pattern="1NXXNXXXXXX",
        trunk_assignments=[assignment],
    )

    xml = build_dialplan(tenant, [], [], [route], [], [], [trunk], [])
    root = fromstring(xml)

    # Find outbound extension
    for dp_ext in root.findall(".//extension"):
        if "outbound" in dp_ext.attrib.get("name", ""):
            actions = {a.attrib.get("application"): a.attrib.get("data") for a in dp_ext.findall(".//action")}
            bridge = actions.get("bridge", "")
            assert "sofia/gateway/acme-clearlyip" in bridge
            break
    else:
        pytest.fail("outbound route extension not found")


def test_dialplan_direct_to_voicemail():
    tenant = make_tenant()
    vm = make_voicemail_box(mailbox_number="100")
    ext = make_extension(extension_number="100", voicemail_box_id=vm.id)

    xml = build_dialplan(tenant, [ext], [], [], [], [vm], [], [])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "direct-vm-100" in ext_names


def test_dialplan_inactive_extension_excluded():
    tenant = make_tenant()
    ext = make_extension(extension_number="100", is_active=False)
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "local-100" not in ext_names


# ── Tests: build_gateway_config ──


def test_gateway_config_basic():
    tenant = make_tenant()
    trunk = make_trunk(tenant_id=tenant.id, name="ClearlyIP")
    passwords = {str(trunk.id): "trunk_pass"}
    tenants = {str(tenant.id): tenant}

    xml = build_gateway_config([trunk], tenants, passwords)
    root = fromstring(xml)

    gw = root.find(".//gateway")
    assert gw is not None
    assert gw.attrib["name"] == "acme-clearlyip"

    params = {p.attrib["name"]: p.attrib["value"] for p in gw.findall("param")}
    assert params["realm"] == "sip.example.com"
    assert params["username"] == "trunk_user"
    assert params["password"] == "trunk_pass"
    assert params["register"] == "true"


def test_gateway_config_ip_auth():
    tenant = make_tenant()
    trunk = make_trunk(tenant_id=tenant.id, name="IP Trunk", auth_type="ip_auth")
    passwords = {}
    tenants = {str(tenant.id): tenant}

    xml = build_gateway_config([trunk], tenants, passwords)
    root = fromstring(xml)

    gw = root.find(".//gateway")
    params = {p.attrib["name"]: p.attrib["value"] for p in gw.findall("param")}
    assert params["register"] == "false"


def test_gateway_config_inactive_trunk_excluded():
    tenant = make_tenant()
    trunk = make_trunk(tenant_id=tenant.id, is_active=False)
    tenants = {str(tenant.id): tenant}

    xml = build_gateway_config([trunk], tenants, {})
    root = fromstring(xml)

    gw = root.find(".//gateway")
    assert gw is None


# ── Tests: Helper functions ──


def test_toll_allow_mapping():
    assert _toll_allow("international") == "domestic,international,local,emergency"
    assert _toll_allow("domestic") == "domestic,local,emergency"
    assert _toll_allow("local") == "local,emergency"
    assert _toll_allow("internal") == "emergency"
    assert _toll_allow("emergency_only") == "emergency"
    assert _toll_allow("unknown") == "emergency"


def test_dial_pattern_to_regex():
    assert _dial_pattern_to_regex("1NXXNXXXXXX") == "^1[2-9][0-9][0-9][2-9][0-9][0-9][0-9][0-9][0-9][0-9]$"
    assert _dial_pattern_to_regex("911") == "^911$"
    assert _dial_pattern_to_regex("NXXXXXX") == "^[2-9][0-9][0-9][0-9][0-9][0-9][0-9]$"
    assert _dial_pattern_to_regex("011.") == "^011.+$"


def test_ring_group_bridge_string_simultaneous():
    ext1 = make_extension(extension_number="100")
    ext2 = make_extension(extension_number="101")
    member1 = make_rg_member(extension_id=ext1.id, position=0)
    member2 = make_rg_member(extension_id=ext2.id, position=1)
    rg = make_ring_group(ring_strategy="simultaneous", members=[member1, member2])

    ext_map = {str(ext1.id): ext1, str(ext2.id): ext2}
    result = _ring_group_bridge_string(rg, ext_map, "acme.sip.local")
    assert result == "user/100@acme.sip.local,user/101@acme.sip.local"


def test_ring_group_bridge_string_sequential():
    ext1 = make_extension(extension_number="100")
    ext2 = make_extension(extension_number="101")
    member1 = make_rg_member(extension_id=ext1.id, position=0)
    member2 = make_rg_member(extension_id=ext2.id, position=1)
    rg = make_ring_group(ring_strategy="sequential", members=[member1, member2])

    ext_map = {str(ext1.id): ext1, str(ext2.id): ext2}
    result = _ring_group_bridge_string(rg, ext_map, "acme.sip.local")
    assert result == "user/100@acme.sip.local|user/101@acme.sip.local"


def test_ring_group_bridge_string_empty():
    rg = make_ring_group(members=[])
    result = _ring_group_bridge_string(rg, {}, "acme.sip.local")
    assert result == ""


def test_ring_group_bridge_string_inactive_member_excluded():
    ext1 = make_extension(extension_number="100", is_active=True)
    ext2 = make_extension(extension_number="101", is_active=False)
    member1 = make_rg_member(extension_id=ext1.id, position=0)
    member2 = make_rg_member(extension_id=ext2.id, position=1)
    rg = make_ring_group(ring_strategy="simultaneous", members=[member1, member2])

    ext_map = {str(ext1.id): ext1, str(ext2.id): ext2}
    result = _ring_group_bridge_string(rg, ext_map, "acme.sip.local")
    assert result == "user/100@acme.sip.local"


# ── Tests: Recording actions in dialplan ──


def test_dialplan_recording_always():
    tenant = make_tenant()
    ext = make_extension(extension_number="100", recording_policy="always")
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            export_actions = [(app, data) for app, data in actions if app == "export"]
            assert len(export_actions) >= 1
            assert "record_session" in export_actions[0][1]
            break
    else:
        pytest.fail("local-100 extension not found")


def test_dialplan_recording_on_demand():
    tenant = make_tenant()
    ext = make_extension(extension_number="100", recording_policy="on_demand")
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            bind_actions = [(app, data) for app, data in actions if app == "bind_meta_app"]
            assert len(bind_actions) >= 1
            assert "record_session" in bind_actions[0][1]
            break
    else:
        pytest.fail("local-100 extension not found")


def test_dialplan_recording_never():
    tenant = make_tenant()
    ext = make_extension(extension_number="100", recording_policy="never")
    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            # Should NOT have any recording-related actions
            for _app, data in actions:
                assert "record_session" not in data, "recording should not be enabled for policy=never"
            break
    else:
        pytest.fail("local-100 extension not found")


# ── Tests: Call waiting variable in directory ──


def test_directory_user_call_waiting_disabled():
    """When call_waiting is False, directory XML should include call_waiting=false variable."""
    tenant = make_tenant()
    ext = make_extension(call_waiting=False)
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert variables["call_waiting"] == "false"


def test_directory_user_call_waiting_enabled():
    """When call_waiting is True, directory XML should NOT include call_waiting variable."""
    tenant = make_tenant()
    ext = make_extension(call_waiting=True)
    xml = build_directory_user(ext, tenant, None, "pass")
    root = fromstring(xml)

    variables = {v.attrib["name"]: v.attrib["value"] for v in root.findall(".//variable")}
    assert "call_waiting" not in variables


# ── Tests: Feature codes *90/*91/*92/*93 ──


def test_dialplan_has_cfb_feature_codes():
    """Dialplan should include *90 (CF busy on) and *91 (CF busy off) feature codes."""
    tenant = make_tenant()
    xml = build_dialplan(tenant, [], [], [], [], [], [], [])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "cfb-on" in ext_names
    assert "cfb-off" in ext_names


def test_dialplan_has_cfna_feature_codes():
    """Dialplan should include *92 (CF no-answer on) and *93 (CF no-answer off) feature codes."""
    tenant = make_tenant()
    xml = build_dialplan(tenant, [], [], [], [], [], [], [])
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert "cfna-on" in ext_names
    assert "cfna-off" in ext_names


def test_cfb_on_uses_db_insert():
    """*90 feature code should use db insert/cfb pattern."""
    tenant = make_tenant()
    xml = build_dialplan(tenant, [], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "cfb-on":
            actions = {a.attrib.get("application"): a.attrib.get("data", "") for a in dp_ext.findall(".//action")}
            assert "db" in actions
            assert "insert/cfb/" in actions["db"]
            break
    else:
        pytest.fail("cfb-on extension not found")


def test_cfna_on_uses_db_insert():
    """*92 feature code should use db insert/cfna pattern."""
    tenant = make_tenant()
    xml = build_dialplan(tenant, [], [], [], [], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "cfna-on":
            actions = {a.attrib.get("application"): a.attrib.get("data", "") for a in dp_ext.findall(".//action")}
            assert "db" in actions
            assert "insert/cfna/" in actions["db"]
            break
    else:
        pytest.fail("cfna-on extension not found")


# ── Tests: Follow-me bridges ──


def make_follow_me_dest(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "follow_me_id": uuid.uuid4(),
        "position": 0,
        "destination": "+15559991234",
        "ring_time": 20,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_follow_me(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "extension_id": uuid.uuid4(),
        "enabled": True,
        "strategy": "sequential",
        "ring_extension_first": True,
        "extension_ring_time": 25,
        "is_active": True,
        "destinations": [],
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_follow_me_sequential_in_dialplan():
    """Follow-me sequential should add multiple bridge actions after primary extension."""
    tenant = make_tenant()
    ext = make_extension(extension_number="100")
    dest1 = make_follow_me_dest(destination="+15559991234", ring_time=20, position=0)
    dest2 = make_follow_me_dest(destination="+15559995678", ring_time=15, position=1)
    fm = make_follow_me(extension_id=ext.id, strategy="sequential", destinations=[dest1, dest2])

    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [], follow_me_configs=[fm])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            bridge_actions = [data for app, data in actions if app == "bridge"]
            # Should have primary ext bridge + 2 follow-me bridges
            assert len(bridge_actions) >= 3
            assert "loopback/+15559991234/acme" in bridge_actions[1]
            assert "loopback/+15559995678/acme" in bridge_actions[2]
            break
    else:
        pytest.fail("local-100 extension not found")


def test_follow_me_ring_all_external_in_dialplan():
    """Follow-me ring_all_external should add single bridge with comma-separated destinations."""
    tenant = make_tenant()
    ext = make_extension(extension_number="100")
    dest1 = make_follow_me_dest(destination="+15559991234", position=0)
    dest2 = make_follow_me_dest(destination="+15559995678", position=1)
    fm = make_follow_me(extension_id=ext.id, strategy="ring_all_external", destinations=[dest1, dest2])

    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [], follow_me_configs=[fm])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            bridge_actions = [data for app, data in actions if app == "bridge"]
            # Should have primary + 1 ring-all bridge
            assert len(bridge_actions) >= 2
            ring_all_bridge = bridge_actions[1]
            assert "," in ring_all_bridge
            assert "loopback/+15559991234/acme" in ring_all_bridge
            assert "loopback/+15559995678/acme" in ring_all_bridge
            break
    else:
        pytest.fail("local-100 extension not found")


def test_follow_me_internal_destination_uses_user():
    """Follow-me destination matching an existing extension should use user/ instead of loopback/."""
    tenant = make_tenant()
    ext100 = make_extension(extension_number="100")
    ext101 = make_extension(extension_number="101")
    dest = make_follow_me_dest(destination="101", position=0)
    fm = make_follow_me(extension_id=ext100.id, strategy="sequential", destinations=[dest])

    xml = build_dialplan(tenant, [ext100, ext101], [], [], [], [], [], [], follow_me_configs=[fm])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            bridge_actions = [data for app, data in actions if app == "bridge"]
            # The follow-me bridge should use user/101@domain
            assert any("user/101@acme.sip.local" in b for b in bridge_actions)
            break
    else:
        pytest.fail("local-100 extension not found")


def test_follow_me_disabled_not_included():
    """Disabled follow-me should not add any extra bridges."""
    tenant = make_tenant()
    ext = make_extension(extension_number="100")
    dest = make_follow_me_dest(destination="+15559991234", position=0)
    fm = make_follow_me(extension_id=ext.id, enabled=False, destinations=[dest])

    xml = build_dialplan(tenant, [ext], [], [], [], [], [], [], follow_me_configs=[fm])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "local-100":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            bridge_actions = [data for app, data in actions if app == "bridge"]
            # Should only have the primary bridge, no follow-me
            assert len(bridge_actions) == 1
            assert "loopback" not in bridge_actions[0]
            break
    else:
        pytest.fail("local-100 extension not found")


# ── Tests: MOH wiring in dialplan ──


def make_audio_prompt(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Hold Music",
        "local_path": "/recordings/prompts/acme/hold-music.wav",
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_dialplan_ring_group_moh():
    """Ring group with moh_prompt_id should set hold_music channel variable."""
    tenant = make_tenant(default_moh_prompt_id=None)
    prompt = make_audio_prompt(local_path="/moh/custom.wav")
    ext1 = make_extension(extension_number="100")
    member = make_rg_member(extension_id=ext1.id, position=0)
    rg = make_ring_group(
        group_number="*601",
        members=[member],
        moh_prompt_id=prompt.id,
    )

    xml = build_dialplan(
        tenant, [ext1], [], [], [rg], [], [], [],
        audio_prompts=[prompt],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "ring-group-*601":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            set_actions = [data for app, data in actions if app == "set"]
            assert any("hold_music=/moh/custom.wav" in s for s in set_actions)
            break
    else:
        pytest.fail("ring group extension not found")


def test_dialplan_tenant_default_moh():
    """Ring group without moh_prompt_id should use tenant default MOH."""
    prompt = make_audio_prompt(local_path="/moh/tenant-default.wav")
    tenant = make_tenant(default_moh_prompt_id=prompt.id)
    ext1 = make_extension(extension_number="100")
    member = make_rg_member(extension_id=ext1.id, position=0)
    rg = make_ring_group(group_number="*601", members=[member], moh_prompt_id=None)

    xml = build_dialplan(
        tenant, [ext1], [], [], [rg], [], [], [],
        audio_prompts=[prompt],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "ring-group-*601":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            set_actions = [data for app, data in actions if app == "set"]
            assert any("hold_music=/moh/tenant-default.wav" in s for s in set_actions)
            break
    else:
        pytest.fail("ring group extension not found")


def test_dialplan_no_moh_when_no_prompt():
    """Ring group without MOH and no tenant default should not set hold_music."""
    tenant = make_tenant(default_moh_prompt_id=None)
    ext1 = make_extension(extension_number="100")
    member = make_rg_member(extension_id=ext1.id, position=0)
    rg = make_ring_group(group_number="*601", members=[member], moh_prompt_id=None)

    xml = build_dialplan(tenant, [ext1], [], [], [rg], [], [], [])
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "ring-group-*601":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            set_actions = [data for app, data in actions if app == "set"]
            assert not any("hold_music" in s for s in set_actions)
            break


def make_queue(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Sales Queue",
        "queue_number": "600",
        "description": None,
        "strategy": "longest-idle-agent",
        "moh_prompt_id": None,
        "max_wait_time": 300,
        "max_wait_time_with_no_agent": 120,
        "tier_rules_apply": True,
        "tier_rule_wait_second": 300,
        "tier_rule_wait_multiply_level": True,
        "tier_rule_no_agent_no_wait": False,
        "discard_abandoned_after": 60,
        "abandoned_resume_allowed": False,
        "caller_exit_key": None,
        "wrapup_time": 0,
        "ring_timeout": 30,
        "announce_frequency": 0,
        "announce_prompt_id": None,
        "overflow_destination_type": None,
        "overflow_destination_id": None,
        "record_calls": False,
        "enabled": True,
        "is_active": True,
        "members": [],
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_dialplan_queue_moh():
    """Queue with moh_prompt_id should set hold_music in dialplan."""
    prompt = make_audio_prompt(local_path="/moh/queue.wav")
    tenant = make_tenant(default_moh_prompt_id=None)
    q = make_queue(moh_prompt_id=prompt.id)

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        queues=[q], audio_prompts=[prompt],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "queue-600":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            set_actions = [data for app, data in actions if app == "set"]
            assert any("hold_music=/moh/queue.wav" in s for s in set_actions)
            break
    else:
        pytest.fail("queue extension not found")


def make_conference(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Test Conf",
        "room_number": "800",
        "description": None,
        "max_participants": 50,
        "participant_pin": None,
        "moderator_pin": None,
        "wait_for_moderator": False,
        "announce_join_leave": True,
        "moh_prompt_id": None,
        "record_conference": False,
        "muted_on_join": False,
        "enabled": True,
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_dialplan_conference_moh():
    """Conference with moh_prompt_id should set conference_moh_sound."""
    prompt = make_audio_prompt(local_path="/moh/conf.wav")
    tenant = make_tenant(default_moh_prompt_id=None)
    cb = make_conference(moh_prompt_id=prompt.id)

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        conference_bridges=[cb], audio_prompts=[prompt],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == "conference-800":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            set_actions = [data for app, data in actions if app == "set"]
            assert any("conference_moh_sound=/moh/conf.wav" in s for s in set_actions)
            break
    else:
        pytest.fail("conference extension not found")


# ── Tests: Caller ID blocklist ──


def make_cid_rule(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Test Rule",
        "rule_type": "block",
        "match_pattern": "anonymous",
        "action": "reject",
        "destination_id": None,
        "priority": 0,
        "notes": None,
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_cid_pattern_to_regex():
    assert _cid_pattern_to_regex("anonymous") == "^(anonymous|Anonymous|unknown|unavailable|Unavailable)$"
    assert _cid_pattern_to_regex("+1555*") == "^\\+?1555.*$"
    assert _cid_pattern_to_regex("+15559991234") == "^\\+?15559991234$"


def test_dialplan_blocklist_reject():
    """Block rule with reject action should add respond 486."""
    tenant = make_tenant(default_moh_prompt_id=None)
    rule = make_cid_rule(
        match_pattern="anonymous",
        action="reject",
        priority=100,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        caller_id_rules=[rule],
    )
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    rule_ext_name = f"cid-rule-{rule.id}"
    assert rule_ext_name in ext_names

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == rule_ext_name:
            assert dp_ext.attrib.get("continue") == "false"
            cond = dp_ext.find("condition")
            assert cond.attrib["field"] == "caller_id_number"
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            assert ("respond", "486 Busy Here") in actions
            break


def test_dialplan_blocklist_hangup():
    """Block rule with hangup action."""
    tenant = make_tenant(default_moh_prompt_id=None)
    rule = make_cid_rule(match_pattern="+1555000", action="hangup")

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        caller_id_rules=[rule],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if f"cid-rule-{rule.id}" == dp_ext.attrib.get("name"):
            actions = [a.attrib.get("application") for a in dp_ext.findall(".//action")]
            assert "hangup" in actions
            break
    else:
        pytest.fail("blocklist extension not found")


def test_dialplan_blocklist_voicemail():
    """Block rule routing to voicemail."""
    tenant = make_tenant(default_moh_prompt_id=None)
    vm = make_voicemail_box(mailbox_number="100")
    rule = make_cid_rule(
        match_pattern="+1800*",
        action="voicemail",
        destination_id=vm.id,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [vm], [], [],
        caller_id_rules=[rule],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if f"cid-rule-{rule.id}" == dp_ext.attrib.get("name"):
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            assert any(app == "voicemail" for app, _ in actions)
            break
    else:
        pytest.fail("blocklist extension not found")


def test_dialplan_allow_rule_continues():
    """Allow rule should have continue='true'."""
    tenant = make_tenant(default_moh_prompt_id=None)
    rule = make_cid_rule(
        match_pattern="+15559991234",
        action="allow",
        rule_type="allow",
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        caller_id_rules=[rule],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if f"cid-rule-{rule.id}" == dp_ext.attrib.get("name"):
            assert dp_ext.attrib.get("continue") == "true"
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            assert ("set", "caller_allowed=true") in actions
            break
    else:
        pytest.fail("allow rule extension not found")


def test_dialplan_blocklist_inactive_excluded():
    """Inactive rules should not appear in dialplan."""
    tenant = make_tenant(default_moh_prompt_id=None)
    rule = make_cid_rule(is_active=False)

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        caller_id_rules=[rule],
    )
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert f"cid-rule-{rule.id}" not in ext_names


def test_dialplan_blocklist_priority_order():
    """Rules should be ordered by priority DESC."""
    tenant = make_tenant(default_moh_prompt_id=None)
    low = make_cid_rule(match_pattern="+1800*", action="reject", priority=10)
    high = make_cid_rule(match_pattern="+1900*", action="hangup", priority=100)

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        caller_id_rules=[low, high],
    )
    root = fromstring(xml)

    # Find positions in extension list
    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    high_pos = ext_names.index(f"cid-rule-{high.id}")
    low_pos = ext_names.index(f"cid-rule-{low.id}")
    assert high_pos < low_pos, "Higher priority should come first"


# ── Tests: Time condition manual override ──


def make_time_condition(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "Business Hours",
        "description": None,
        "timezone": "America/New_York",
        "rules": [
            {"type": "day_of_week", "days": [1, 2, 3, 4, 5]},
            {"type": "time_of_day", "start_time": "08:00", "end_time": "17:00"},
        ],
        "match_destination_type": "extension",
        "match_destination_id": None,
        "nomatch_destination_type": "voicemail",
        "nomatch_destination_id": None,
        "holiday_calendar_id": None,
        "holiday_calendar": None,
        "manual_override": None,
        "enabled": True,
        "is_active": True,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_tc_manual_override_day():
    """manual_override='day' should route to match destination unconditionally."""
    tenant = make_tenant(default_moh_prompt_id=None)
    ext = make_extension(extension_number="100")
    tc = make_time_condition(
        manual_override="day",
        match_destination_type="extension",
        match_destination_id=ext.id,
        nomatch_destination_type="voicemail",
    )

    xml = build_dialplan(
        tenant, [ext], [], [], [], [], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == f"tc-{tc.id}":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            # Should have transfer to extension, not time conditions
            assert any(app == "transfer" for app, _ in actions)
            # Should not have time-matching condition
            conditions = dp_ext.findall("condition")
            for cond in conditions:
                assert "wday" not in cond.attrib
                assert "time-of-day" not in cond.attrib
            break
    else:
        pytest.fail("TC extension not found")


def test_tc_manual_override_night():
    """manual_override='night' should route to nomatch destination unconditionally."""
    tenant = make_tenant(default_moh_prompt_id=None)
    vm = make_voicemail_box(mailbox_number="100")
    tc = make_time_condition(
        manual_override="night",
        match_destination_type="extension",
        nomatch_destination_type="voicemail",
        nomatch_destination_id=vm.id,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [vm], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == f"tc-{tc.id}":
            actions = [(a.attrib.get("application"), a.attrib.get("data", "")) for a in dp_ext.findall(".//action")]
            # Should have voicemail action
            assert any(app == "voicemail" for app, _ in actions)
            break
    else:
        pytest.fail("TC extension not found")


# ── Tests: Holiday calendar preemption ──


def make_holiday_entry(**overrides):
    from datetime import date
    defaults = {
        "id": uuid.uuid4(),
        "calendar_id": uuid.uuid4(),
        "name": "Test Holiday",
        "date": date(2026, 12, 25),
        "recur_annually": True,
        "all_day": True,
        "start_time": None,
        "end_time": None,
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def make_holiday_calendar(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "name": "US Holidays",
        "description": None,
        "is_active": True,
        "entries": [],
    }
    defaults.update(overrides)
    return FakeObj(**defaults)


def test_tc_holiday_preemption():
    """Holiday entries should create preemption extensions before main TC."""
    from datetime import date
    tenant = make_tenant(default_moh_prompt_id=None)
    vm = make_voicemail_box(mailbox_number="100")
    entry = make_holiday_entry(
        name="Christmas",
        date=date(2026, 12, 25),
        recur_annually=True,
        all_day=True,
    )
    calendar = make_holiday_calendar(entries=[entry])
    tc = make_time_condition(
        holiday_calendar_id=calendar.id,
        holiday_calendar=calendar,
        nomatch_destination_type="voicemail",
        nomatch_destination_id=vm.id,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [vm], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    holiday_ext_name = f"tc-{tc.id}-holiday-{entry.id}"
    assert holiday_ext_name in ext_names

    # Holiday ext should come before main TC ext
    holiday_pos = ext_names.index(holiday_ext_name)
    main_pos = ext_names.index(f"tc-{tc.id}")
    assert holiday_pos < main_pos


def test_tc_holiday_partial_day():
    """Partial-day holiday should include time-of-day in condition."""
    from datetime import date, time
    tenant = make_tenant(default_moh_prompt_id=None)
    vm = make_voicemail_box(mailbox_number="100")
    entry = make_holiday_entry(
        name="Christmas Eve Afternoon",
        date=date(2026, 12, 24),
        recur_annually=True,
        all_day=False,
        start_time=time(12, 0),
        end_time=time(23, 59),
    )
    calendar = make_holiday_calendar(entries=[entry])
    tc = make_time_condition(
        holiday_calendar_id=calendar.id,
        holiday_calendar=calendar,
        nomatch_destination_type="voicemail",
        nomatch_destination_id=vm.id,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [vm], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == f"tc-{tc.id}-holiday-{entry.id}":
            conditions = dp_ext.findall("condition")
            # Should have date-matching condition with time-of-day
            date_cond = [c for c in conditions if c.attrib.get("mon")]
            assert len(date_cond) == 1
            assert date_cond[0].attrib.get("time-of-day") == "12:00-23:59"
            break
    else:
        pytest.fail("Holiday extension not found")


def test_tc_holiday_non_recurring():
    """Non-recurring holiday should include year in condition."""
    from datetime import date
    tenant = make_tenant(default_moh_prompt_id=None)
    vm = make_voicemail_box(mailbox_number="100")
    entry = make_holiday_entry(
        name="Thanksgiving 2026",
        date=date(2026, 11, 26),
        recur_annually=False,
        all_day=True,
    )
    calendar = make_holiday_calendar(entries=[entry])
    tc = make_time_condition(
        holiday_calendar_id=calendar.id,
        holiday_calendar=calendar,
        nomatch_destination_type="voicemail",
        nomatch_destination_id=vm.id,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [vm], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    for dp_ext in root.findall(".//extension"):
        if dp_ext.attrib.get("name") == f"tc-{tc.id}-holiday-{entry.id}":
            conditions = dp_ext.findall("condition")
            date_cond = [c for c in conditions if c.attrib.get("mon")]
            assert len(date_cond) == 1
            assert date_cond[0].attrib.get("year") == "2026"
            break
    else:
        pytest.fail("Holiday extension not found")


def test_tc_inactive_calendar_ignored():
    """Inactive holiday calendar should not generate holiday extensions."""
    from datetime import date
    tenant = make_tenant(default_moh_prompt_id=None)
    entry = make_holiday_entry(date=date(2026, 12, 25))
    calendar = make_holiday_calendar(is_active=False, entries=[entry])
    tc = make_time_condition(
        holiday_calendar_id=calendar.id,
        holiday_calendar=calendar,
    )

    xml = build_dialplan(
        tenant, [], [], [], [], [], [], [],
        time_conditions=[tc],
    )
    root = fromstring(xml)

    ext_names = [e.attrib["name"] for e in root.findall(".//extension")]
    assert not any("holiday" in name for name in ext_names)
