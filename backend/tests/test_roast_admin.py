"""Tests for the Roast Wall, admin project CRUD, reactions, logs, and resume."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.content_store as content_store
import app.resume as resume
from app.main import app
from app.rate_limit import board_limiter


@pytest.fixture(autouse=True)
def isolated_content(tmp_path, monkeypatch):
    monkeypatch.setattr(content_store, "ROASTS_FILE", tmp_path / "roast_wall.json")
    monkeypatch.setattr(content_store, "PROJECTS_FILE", tmp_path / "custom_projects.json")
    monkeypatch.setattr(content_store, "REACTIONS_FILE", tmp_path / "reactions.json")
    monkeypatch.setattr(content_store, "LOGS_FILE", tmp_path / "admin_logs.json")
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setattr(board_limiter, "max_requests", 1000)
    board_limiter._hits.clear()
    resume._cache = None
    yield


@pytest.fixture()
def client():
    return TestClient(app)


def admin_headers():
    return {"X-Admin-Key": "test-admin-key"}


def test_roast_wall_is_anonymous_and_moderated(client):
    submitted = client.post(
        "/api/roasts",
        json={
            "text": "This portfolio has too many features, but at least it ships.",
            "advice": "Lead with the case studies and hide the experiments deeper.",
        },
    )
    assert submitted.status_code == 200
    roast_id = submitted.json()["id"]
    assert submitted.json()["status"] == "pending"

    assert client.get("/api/roasts").json() == []
    assert client.get("/api/admin/roasts").status_code == 401

    pending = client.get("/api/admin/roasts?status=pending", headers=admin_headers())
    assert pending.status_code == 200
    assert pending.json()[0]["id"] == roast_id
    assert "email" not in pending.text.lower()

    approved = client.post(
        f"/api/admin/roasts/{roast_id}/approve",
        json={"note": "Useful and anonymous."},
        headers=admin_headers(),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    public = client.get("/api/roasts").json()
    assert len(public) == 1
    assert set(public[0]) == {"id", "author", "target", "text", "advice", "created_at"}
    assert "company" not in public[0]
    assert "email" not in public[0]


def test_roast_reject_and_delete(client):
    first = client.post(
        "/api/roasts", json={"text": "A rejected roast for the moderation queue."}
    ).json()["id"]
    second = client.post(
        "/api/roasts", json={"text": "A roast that will be deleted entirely."}
    ).json()["id"]

    assert (
        client.post(
            f"/api/admin/roasts/{first}/reject",
            json={"note": "Too vague."},
            headers=admin_headers(),
        ).json()["status"]
        == "rejected"
    )
    assert client.get("/api/roasts").json() == []

    deleted = client.delete(
        f"/api/admin/roasts/{second}", headers=admin_headers()
    )
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True


def test_admin_project_crud_updates_projects_resume_and_logs(client):
    before_resume = client.get("/api/resume")
    assert before_resume.status_code == 200

    created = client.post(
        "/api/admin/projects",
        headers=admin_headers(),
        json={
            "title": "Warehouse Signal API",
            "problem": "Small shops cannot see stock movements across branches.",
            "build": "FastAPI service with PostgreSQL, signed webhooks, and a Vue dashboard.",
            "outcome": "Inventory alerts reach managers before stockouts happen.",
            "stack": ["FastAPI", "PostgreSQL", "Vue 3"],
            "repo_url": "https://github.com/wachiraericksonkynua/warehouse-signal",
            "demo_url": "https://example.com/warehouse-signal",
        },
    )
    assert created.status_code == 200
    project = created.json()
    project_id = project["id"]
    assert project["custom"] is True
    assert project["title"] == "Warehouse Signal API"

    projects = client.get("/api/projects").json()
    assert any(item["id"] == project_id for item in projects)
    created_public = next(item for item in projects if item["id"] == project_id)
    assert created_public["reactions"] == {"heart": 0, "roast": 0}
    assert created_public["demo_url"].startswith("https://")

    resume_payload = client.get("/api/resume.json").json()
    assert any(
        item.get("name") == "Warehouse Signal API"
        for item in resume_payload["projects"]
    )

    after_resume = client.get("/api/resume")
    assert after_resume.status_code == 200
    assert after_resume.content != before_resume.content
    assert after_resume.headers["content-type"].startswith("application/pdf")

    logs = client.get("/api/admin/logs", headers=admin_headers()).json()
    assert any(log["action"] == "project.create" for log in logs)

    updated = client.put(
        f"/api/admin/projects/{project_id}",
        headers=admin_headers(),
        json={"title": "Warehouse Signal API v2"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Warehouse Signal API v2"

    deleted = client.delete(
        f"/api/admin/projects/{project_id}", headers=admin_headers()
    )
    assert deleted.status_code == 200
    assert not any(
        item["id"] == project_id for item in client.get("/api/projects").json()
    )


def test_project_reactions_persist_and_are_counted(client):
    response = client.post(
        "/api/projects/ayutech/reactions", json={"reaction": "heart"}
    )
    assert response.status_code == 200
    assert response.json() == {"heart": 1, "roast": 0}

    response = client.post(
        "/api/projects/ayutech/reactions", json={"reaction": "roast"}
    )
    assert response.json() == {"heart": 1, "roast": 1}

    project = next(
        item for item in client.get("/api/projects").json() if item["id"] == "ayutech"
    )
    assert project["reactions"] == {"heart": 1, "roast": 1}

    assert (
        client.post(
            "/api/projects/missing/reactions", json={"reaction": "heart"}
        ).status_code
        == 404
    )


def test_keepalive_endpoint_works_with_json_fallback(client):
    response = client.get("/api/keepalive")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "json-fallback"
    assert data["checked_at"]


def test_admin_project_routes_require_admin_key(client):
    assert client.get("/api/admin/projects").status_code == 401
    assert client.get("/api/admin/logs").status_code == 401
    assert (
        client.post(
            "/api/admin/projects",
            json={
                "title": "No auth",
                "problem": "This request should not be accepted.",
                "build": "Nothing should be written.",
                "outcome": "Rejected.",
                "stack": ["Python"],
            },
        ).status_code
        == 401
    )
