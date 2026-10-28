import json

from fastapi.testclient import TestClient

import app.bookings as bookings
import app.pet as pet
from app.main import app
from app.rate_limit import interact_limiter


def make_client(tmp_path, monkeypatch):
    monkeypatch.setattr(bookings, "BOOKINGS_FILE", tmp_path / "bookings.json")
    monkeypatch.setattr(pet, "STATE_FILE", tmp_path / "pet_state.json")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DIRECT_URL", "")
    interact_limiter._hits.clear()
    return TestClient(app)


def test_booking_persists_and_relieves_desperation(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/book",
        json={
            "name": "Ada Lovelace",
            "company": "Analytical Engines",
            "contact": "ada@example.com",
            "role": "Backend Engineer",
            "preferred_time": "Tuesday morning",
            "message": "Looking forward to it.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["booking"]["name"] == "Ada Lovelace"
    assert body["pet_state"]["relief_gained"] == 20

    persisted = json.loads((tmp_path / "bookings.json").read_text(encoding="utf-8"))
    assert persisted[0]["contact"] == "ada@example.com"


def test_admin_leads_requires_header_and_returns_data(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    client.post(
        "/api/book",
        json={"name": "Grace Hopper", "contact": "grace@example.com"},
    )

    assert client.get("/api/admin/leads").status_code == 401
    assert (
        client.get(
            "/api/admin/leads", headers={"X-Admin-Key": "wrong-key"}
        ).status_code
        == 401
    )

    response = client.get(
        "/api/admin/leads", headers={"X-Admin-Key": "test-admin-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bookings"][0]["name"] == "Grace Hopper"


def test_pet_interaction_is_available_as_admin_lead(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    response = client.post(
        "/api/pet/interact",
        json={"type": "link", "note": "https://example.com/jobs/backend"},
    )
    assert response.status_code == 200

    leads = client.get(
        "/api/admin/leads", headers={"X-Admin-Key": "test-admin-key"}
    ).json()["pet_leads"]
    assert any(
        lead["note"] == "https://example.com/jobs/backend" for lead in leads
    )
