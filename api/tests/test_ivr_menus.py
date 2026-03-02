import uuid

import pytest
from httpx import AsyncClient

from .conftest import ACME_TENANT_ID, MSP_TENANT_ID, auth_header

BASE = f"/api/v1/tenants/{ACME_TENANT_ID}/ivr-menus"
IVR_ID = "b4000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_ivr_menus(client: AsyncClient, msp_admin_token: str):
    response = await client.get(BASE, headers=auth_header(msp_admin_token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_ivr_menu(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{IVR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Main Menu"
    assert data["timeout"] == 10
    assert isinstance(data["options"], list)
    assert len(data["options"]) >= 3


@pytest.mark.asyncio
async def test_get_ivr_menu_options_details(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{IVR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    options = data["options"]

    # Check option 1 (extension)
    opt_1 = next((o for o in options if o["digits"] == "1"), None)
    assert opt_1 is not None
    assert opt_1["action_type"] == "extension"
    assert opt_1["label"] == "Press 1 for Admin"


@pytest.mark.asyncio
async def test_get_ivr_not_found(client: AsyncClient, msp_admin_token: str):
    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"{BASE}/{fake_id}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_ivr_menu(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": f"Support Menu {uuid.uuid4().hex[:8]}",
            "description": "Support IVR",
            "timeout": 15,
            "max_failures": 5,
            "digit_len": 1,
            "options": [
                {
                    "digits": "1",
                    "action_type": "extension",
                    "action_target_value": "100",
                    "label": "Press 1 for Support",
                    "position": 0,
                },
                {
                    "digits": "9",
                    "action_type": "hangup",
                    "label": "Press 9 to hang up",
                    "position": 1,
                },
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["timeout"] == 15
    assert data["max_failures"] == 5
    assert len(data["options"]) == 2


@pytest.mark.asyncio
async def test_create_duplicate_name_fails(client: AsyncClient, msp_admin_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(msp_admin_token),
        json={
            "name": "Main Menu",
            "options": [],
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_ivr_menu(client: AsyncClient, msp_admin_token: str):
    response = await client.patch(
        f"{BASE}/{IVR_ID}",
        headers=auth_header(msp_admin_token),
        json={"description": "Updated IVR description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated IVR description"


@pytest.mark.asyncio
async def test_update_ivr_replace_options(client: AsyncClient, msp_admin_token: str):
    """Options are replaced wholesale on update."""
    response = await client.patch(
        f"{BASE}/{IVR_ID}",
        headers=auth_header(msp_admin_token),
        json={
            "options": [
                {
                    "digits": "1",
                    "action_type": "extension",
                    "action_target_value": "100",
                    "label": "Press 1 for Admin",
                    "position": 0,
                },
                {
                    "digits": "2",
                    "action_type": "ring_group",
                    "action_target_value": "*601",
                    "label": "Press 2 for Sales",
                    "position": 1,
                },
                {
                    "digits": "0",
                    "action_type": "voicemail",
                    "action_target_value": "100",
                    "label": "Press 0 for Voicemail",
                    "position": 2,
                },
                {
                    "digits": "*",
                    "action_type": "repeat",
                    "label": "Press * to repeat",
                    "position": 3,
                },
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["options"]) == 4


@pytest.mark.asyncio
async def test_tenant_user_cannot_view_ivr(client: AsyncClient, acme_user_token: str):
    response = await client.get(BASE, headers=auth_header(acme_user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tenant_manager_can_view_ivr(client: AsyncClient, acme_manager_token: str):
    response = await client.get(BASE, headers=auth_header(acme_manager_token))
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_manager_cannot_create_ivr(client: AsyncClient, acme_manager_token: str):
    response = await client.post(
        BASE,
        headers=auth_header(acme_manager_token),
        json={"name": "Manager IVR", "options": []},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(client: AsyncClient, acme_admin_token: str):
    other = f"/api/v1/tenants/{MSP_TENANT_ID}/ivr-menus"
    response = await client.get(other, headers=auth_header(acme_admin_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ivr_response_has_all_fields(client: AsyncClient, msp_admin_token: str):
    response = await client.get(
        f"{BASE}/{IVR_ID}", headers=auth_header(msp_admin_token)
    )
    assert response.status_code == 200
    data = response.json()
    required_fields = [
        "id", "tenant_id", "name", "description",
        "greet_long_prompt_id", "greet_short_prompt_id",
        "invalid_sound_prompt_id", "exit_sound_prompt_id",
        "timeout", "max_failures", "max_timeouts",
        "inter_digit_timeout", "digit_len",
        "exit_destination_type", "exit_destination_id",
        "enabled", "is_active", "created_at", "updated_at", "options",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"
