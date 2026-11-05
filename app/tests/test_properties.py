from conftest import TENANT_A, TEST_APP_DATABASE_URL
from helpers import auth_headers, login, seed_user


async def _staff_headers(client) -> dict:
    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email="board@sunsetridge.test",
        password="correct-horse",
        role="board_member",
    )
    token = await login(client, "board@sunsetridge.test", "correct-horse")
    return auth_headers(token)


async def test_create_and_read_property(client):
    headers = await _staff_headers(client)

    create_resp = await client.post(
        "/api/v1/properties",
        json={
            "name": "Sunset Ridge Clubhouse",
            "address_line1": "100 Sunset Blvd",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    property_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/properties", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = await client.get(f"/api/v1/properties/{property_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Sunset Ridge Clubhouse"


async def test_update_and_delete_property(client):
    headers = await _staff_headers(client)
    create_resp = await client.post(
        "/api/v1/properties",
        json={
            "name": "Original Name",
            "address_line1": "1 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
        headers=headers,
    )
    property_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/properties/{property_id}", json={"name": "Renamed"}, headers=headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed"

    delete_resp = await client.delete(f"/api/v1/properties/{property_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/properties/{property_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_resident_cannot_create_property(client):
    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email="resident@sunsetridge.test",
        password="correct-horse",
        role="resident",
    )
    token = await login(client, "resident@sunsetridge.test", "correct-horse")

    resp = await client.post(
        "/api/v1/properties",
        json={
            "name": "Should Fail",
            "address_line1": "1 Main St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/api/v1/properties")
    assert resp.status_code == 401
