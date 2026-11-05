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
        json={"property_id": property_id, "unit_number": "12B"},
        headers=headers,
    )
    return unit_resp.json()["id"]


async def test_invoice_status_transitions_as_payments_are_recorded(client):
    headers = await _staff_headers(client)
    unit_id = await _create_unit(client, headers)

    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "unit_id": unit_id,
            "amount_cents": 20000,
            "due_date": "2026-12-01",
            "period_start": "2026-12-01",
            "period_end": "2026-12-31",
        },
        headers=headers,
    )
    assert invoice_resp.status_code == 201
    invoice = invoice_resp.json()
    assert invoice["status"] == "unpaid"

    partial_payment = await client.post(
        "/api/v1/payments",
        json={
            "invoice_id": invoice["id"],
            "amount_cents": 5000,
            "paid_at": "2026-12-05T00:00:00Z",
            "method": "ach",
        },
        headers=headers,
    )
    assert partial_payment.status_code == 201
    invoice_after_partial = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
    assert invoice_after_partial.json()["status"] == "partial"

    final_payment = await client.post(
        "/api/v1/payments",
        json={
            "invoice_id": invoice["id"],
            "amount_cents": 15000,
            "paid_at": "2026-12-10T00:00:00Z",
            "method": "card",
        },
        headers=headers,
    )
    assert final_payment.status_code == 201
    invoice_after_full = await client.get(f"/api/v1/invoices/{invoice['id']}", headers=headers)
    assert invoice_after_full.json()["status"] == "paid"


async def test_resident_only_sees_own_unit_invoices(client):
    headers = await _staff_headers(client)
    own_unit_id = await _create_unit(client, headers)
    other_unit_id = await _create_unit(client, headers)

    resident_resp = await client.post(
        "/api/v1/residents",
        json={
            "unit_id": own_unit_id,
            "first_name": "Jamie",
            "last_name": "Rivera",
            "email": "jamie@example.com",
            "is_owner": True,
        },
        headers=headers,
    )
    resident_id = resident_resp.json()["id"]

    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email="jamie@example.com",
        password="correct-horse",
        role="resident",
        resident_id=resident_id,
    )

    own_invoice = await client.post(
        "/api/v1/invoices",
        json={
            "unit_id": own_unit_id,
            "amount_cents": 10000,
            "due_date": "2026-12-01",
            "period_start": "2026-12-01",
            "period_end": "2026-12-31",
        },
        headers=headers,
    )
    other_invoice = await client.post(
        "/api/v1/invoices",
        json={
            "unit_id": other_unit_id,
            "amount_cents": 10000,
            "due_date": "2026-12-01",
            "period_start": "2026-12-01",
            "period_end": "2026-12-31",
        },
        headers=headers,
    )

    resident_token = await login(client, "jamie@example.com", "correct-horse")
    resident_headers = auth_headers(resident_token)

    list_resp = await client.get("/api/v1/invoices", headers=resident_headers)
    assert list_resp.status_code == 200
    seen_ids = {inv["id"] for inv in list_resp.json()}
    assert seen_ids == {own_invoice.json()["id"]}

    forbidden_resp = await client.get(
        f"/api/v1/invoices/{other_invoice.json()['id']}", headers=resident_headers
    )
    assert forbidden_resp.status_code == 404


async def test_resident_cannot_create_invoice(client):
    headers = await _staff_headers(client)
    unit_id = await _create_unit(client, headers)
    resident_resp = await client.post(
        "/api/v1/residents",
        json={
            "unit_id": unit_id,
            "first_name": "Jamie",
            "last_name": "Rivera",
            "email": "jamie2@example.com",
            "is_owner": True,
        },
        headers=headers,
    )
    resident_id = resident_resp.json()["id"]
    await seed_user(
        TEST_APP_DATABASE_URL,
        TENANT_A,
        email="jamie2@example.com",
        password="correct-horse",
        role="resident",
        resident_id=resident_id,
    )
    resident_token = await login(client, "jamie2@example.com", "correct-horse")

    resp = await client.post(
        "/api/v1/invoices",
        json={
            "unit_id": unit_id,
            "amount_cents": 10000,
            "due_date": "2026-12-01",
            "period_start": "2026-12-01",
            "period_end": "2026-12-31",
        },
        headers=auth_headers(resident_token),
    )
    assert resp.status_code == 403
