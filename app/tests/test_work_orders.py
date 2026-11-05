from conftest import TENANT_A, TEST_APP_DATABASE_URL
from helpers import auth_headers, login, seed_user


async def _staff_headers(client, email: str = "board@sunsetridge.test") -> dict:
    await seed_user(
        TEST_APP_DATABASE_URL, TENANT_A, email=email, password="correct-horse", role="board_member"
    )
    token = await login(client, email, "correct-horse")
    return auth_headers(token)


async def _create_unit(client, headers) -> str:
    prop_resp = await client.post(
        "/api/v1/properties",
        json={
            "name": "Sunset Ridge",
            "address_line1": "100 Sunset Blvd",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
        headers=headers,
    )
    property_id = prop_resp.json()["id"]
    unit_resp = await client.post(
        "/api/v1/units",
        json={"property_id": property_id, "unit_number": "7A"},
        headers=headers,
    )
    return unit_resp.json()["id"]


async def _create_resident_user(client, headers, unit_id: str, email: str) -> str:
    resident_resp = await client.post(
        "/api/v1/residents",
        json={
            "unit_id": unit_id,
            "first_name": "Jamie",
            "last_name": "Rivera",
            "email": email,
            "is_owner": True,
        },
        headers=headers,
    )
    resident_id = resident_resp.json()["id"]
    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email=email,
        password="correct-horse",
        role="resident",
        resident_id=resident_id,
    )
    token = await login(client, email, "correct-horse")
    return token


async def test_resident_can_file_and_view_own_work_order(client):
    headers = await _staff_headers(client)
    unit_id = await _create_unit(client, headers)
    resident_token = await _create_resident_user(client, headers, unit_id, "resident@example.com")

    create_resp = await client.post(
        "/api/v1/work-orders",
        json={"unit_id": unit_id, "title": "Leaky faucet", "priority": "medium"},
        headers=auth_headers(resident_token),
    )
    assert create_resp.status_code == 201
    work_order = create_resp.json()
    assert work_order["status"] == "open"
    assert work_order["requested_by_resident_id"] is not None

    list_resp = await client.get("/api/v1/work-orders", headers=auth_headers(resident_token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_resident_cannot_file_work_order_for_another_unit(client):
    headers = await _staff_headers(client)
    own_unit_id = await _create_unit(client, headers)
    other_unit_id = await _create_unit(client, headers)
    resident_token = await _create_resident_user(
        client, headers, own_unit_id, "resident2@example.com"
    )

    resp = await client.post(
        "/api/v1/work-orders",
        json={"unit_id": other_unit_id, "title": "Not my unit"},
        headers=auth_headers(resident_token),
    )
    assert resp.status_code == 403


async def test_resident_cannot_change_work_order_status(client):
    headers = await _staff_headers(client)
    unit_id = await _create_unit(client, headers)
    resident_token = await _create_resident_user(client, headers, unit_id, "resident3@example.com")

    create_resp = await client.post(
        "/api/v1/work-orders",
        json={"unit_id": unit_id, "title": "Broken window"},
        headers=auth_headers(resident_token),
    )
    work_order_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/work-orders/{work_order_id}",
        json={"status": "completed"},
        headers=auth_headers(resident_token),
    )
    assert patch_resp.status_code == 403


async def test_staff_completing_work_order_sets_completed_at(client):
    headers = await _staff_headers(client)
    unit_id = await _create_unit(client, headers)

    create_resp = await client.post(
        "/api/v1/work-orders",
        json={"unit_id": unit_id, "title": "Repaint hallway"},
        headers=headers,
    )
    work_order_id = create_resp.json()["id"]
    assert create_resp.json()["completed_at"] is None

    patch_resp = await client.patch(
        f"/api/v1/work-orders/{work_order_id}",
        json={"status": "completed", "assigned_to": "Acme Painters"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["status"] == "completed"
    assert body["assigned_to"] == "Acme Painters"
    assert body["completed_at"] is not None
