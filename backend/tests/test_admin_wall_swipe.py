"""Regression tests for the Roast Wall, swipe reactions, and admin workflows."""

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
    monkeypatch.setattr(resume, "OVERRIDE_FILE", tmp_path / "resume_override.json")
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


def test_roast_is_hidden_until_admin_approves(client):
    submitted = client.post(
        "/api/roast-wall",
        json={
            "text": "The swipe deck is fun but the resume needs fewer buzzwords.",
            "target": "Resume Copy",
        },
    )
    assert submitted.status_code == 200
    roast_id = submitted.json()["id"]
    assert submitted.json()["status"] == "pending"
    assert "moderation queue" in submitted.json()["message"]

    public = client.get("/api/roast-wall")
    assert public.status_code == 200
    assert all(item["id"] != roast_id for item in public.json())

    pending = client.get("/api/admin/moderation", headers=admin_headers())
    assert pending.status_code == 200
    assert any(item["id"] == roast_id for item in pending.json()["roasts"])

    approved = client.post(
        f"/api/admin/roast/{roast_id}/approve",
        json={"note": "Approved in test."},
        headers=admin_headers(),
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    public = client.get("/api/roast-wall").json()
    live = next(item for item in public if item["id"] == roast_id)
    assert live["author"] == "@anonymous_dev"
    assert live["target"] == "Resume Copy"
    assert live["text"].startswith("The swipe deck is fun")
    for forbidden in ("email", "ip", "company"):
        assert forbidden not in live


def test_project_with_include_in_resume_updates_pdf(client):
    created = client.post(
        "/api/admin/projects",
        headers=admin_headers(),
        json={
            "title": "Resume Include Test Project",
            "category": "AI & Full-Stack",
            "problem": "The PDF must prove that dashboard edits reach the download.",
            "build": "FastAPI stores the project and fpdf2 renders it on demand.",
            "outcome": "The generated PDF contains the new project title.",
            "stack": ["FastAPI", "fpdf2", "pytest"],
            "repo_url": "https://github.com/example/resume-include-test",
            "live_url": "https://example.com/resume-include-test",
            "include_in_resume": True,
        },
    )
    assert created.status_code == 200
    project = created.json()
    assert project["include_in_resume"] is True
    assert project["category"] == "AI & Full-Stack"

    resume_json = client.get("/api/resume.json").json()
    assert any(
        item.get("name") == "Resume Include Test Project"
        for item in resume_json["projects"]
    )

    pdf = client.get("/api/resume")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert b"Resume Include Test Project" in pdf.content


def test_project_can_be_hidden_from_resume(client):
    created = client.post(
        "/api/admin/projects",
        headers=admin_headers(),
        json={
            "title": "Hidden Resume Project",
            "problem": "This project is for the portfolio but not the resume.",
            "build": "Stored with include_in_resume set to false.",
            "outcome": "The PDF must not contain this title.",
            "stack": ["Python"],
            "include_in_resume": False,
        },
    )
    assert created.status_code == 200

    auth = client.put(
        "/api/admin/resume",
        headers=admin_headers(),
        json={"summary": "Owner-edited summary for the live resume."},
    )
    assert auth.status_code == 200
    assert auth.json()["resume"]["summary"] == "Owner-edited summary for the live resume."

    pdf = client.get("/api/resume")
    assert pdf.content.startswith(b"%PDF")
    assert b"Hidden Resume Project" not in pdf.content
    assert b"Owner-edited summary for the live resume." in pdf.content


def test_admin_routes_reject_missing_or_wrong_key(client):
    assert client.get("/api/admin/leads").status_code == 401
    assert client.get("/api/admin/moderation").status_code == 401
    assert client.put("/api/admin/resume", json={"summary": "nope"}).status_code == 401
    assert (
        client.delete(
            "/api/admin/roast/does-not-matter",
            headers={"X-Admin-Key": "wrong-key"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/admin/projects",
            json={
                "title": "Unauthorized project",
                "problem": "This request must never be accepted.",
                "build": "No writes should happen.",
                "outcome": "Rejected.",
                "stack": ["Python"],
            },
        ).status_code
        == 401
    )


def test_swipe_react_alias_records_heart(client):
    response = client.post(
        "/api/projects/ayutech/react", json={"reaction": "heart"}
    )
    assert response.status_code == 200
    assert response.json() == {"heart": 1, "roast": 0}

    public = client.get("/api/projects").json()
    project = next(item for item in public if item["id"] == "ayutech")
    assert project["reactions"] == {"heart": 1, "roast": 0}
