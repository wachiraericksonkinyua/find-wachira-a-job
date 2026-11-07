"""Phase 7/8 tests: funnel analytics, talent board, and SSRF-safe apply assistant."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.apply_assistant as apply_assistant
import app.board as board
import app.bookings as bookings
import app.pet as pet
import app.redteam as redteam
from app.llm import LLMError
from app.main import app
from app.match import CitationItem, MatchResponse
from app.rate_limit import (
    analytics_limiter,
    apply_limiter,
    board_limiter,
    interact_limiter,
    llm_limiter,
)

PRIVATE_URLS = [
    "http://127.0.0.1",
    "http://localhost",
    "http://169.254.169.254/latest/meta-data/",
    "file:///etc/passwd",
    "http://10.0.0.5/internal",
    "http://[::1]/admin",
]


@pytest.fixture(autouse=True)
def isolated_phase7_8_state(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "BOARD_STATE_FILE", tmp_path / "board_state.json")
    monkeypatch.setattr(apply_assistant, "JOBS_FILE", tmp_path / "apply_jobs.json")
    monkeypatch.setattr(bookings, "BOOKINGS_FILE", tmp_path / "bookings.json")
    monkeypatch.setattr(pet, "STATE_FILE", tmp_path / "pet_state.json")
    monkeypatch.setattr(redteam, "STATE_FILE", tmp_path / "redteam_state.json")
    monkeypatch.setattr(redteam, "_connect_postgres", lambda: None)
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DIRECT_URL", "")

    for limiter in (
        analytics_limiter,
        apply_limiter,
        board_limiter,
        interact_limiter,
        llm_limiter,
    ):
        monkeypatch.setattr(limiter, "max_requests", 1000)
        limiter._hits.clear()

    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def fake_match(monkeypatch):
    def run(req):
        return MatchResponse(
            score=78,
            verdict="Strong backend fit grounded in real project evidence.",
            matched_skills=["Python", "FastAPI", "PostgreSQL"],
            gaps=["Docker"],
            citations=[
                CitationItem(
                    project_slug="ayutech",
                    project_title="AyuTech Motors",
                    section="build",
                    text="FastAPI + Supabase + M-Pesa Daraja STK Push.",
                    similarity=0.91,
                )
            ],
        )

    monkeypatch.setattr(apply_assistant, "run_match", run)

    def fail_llm(*args, **kwargs):
        raise LLMError("offline")

    monkeypatch.setattr(apply_assistant, "complete", fail_llm)
    return run


def test_ssrf_validator_blocks_private_and_non_http_targets():
    for url in PRIVATE_URLS:
        with pytest.raises(ValueError):
            apply_assistant.validate_public_url(url)


def test_analyze_endpoint_rejects_ssrf_before_any_fetch(client, monkeypatch):
    def fail_fetch(*args, **kwargs):
        raise AssertionError("unsafe URL reached the fetcher")

    monkeypatch.setattr(apply_assistant.httpx, "stream", fail_fetch)

    for url in PRIVATE_URLS:
        response = client.post("/api/apply/analyze", json={"url": url})
        assert response.status_code == 400, url


def test_talent_board_seeds_approved_entries_without_private_fields(client):
    response = client.get("/api/board")
    assert response.status_code == 200

    entries = response.json()
    assert len(entries) == 2
    assert {entry["name"] for entry in entries} == {"Amina Otieno", "Brian Kimani"}
    for entry in entries:
        assert set(entry) == {"id", "name", "role", "pitch", "link"}
        assert entry["link"].startswith("https://")
        assert "email" not in entry
        assert "takedown_token" not in entry
        assert "status" not in entry


def test_board_submission_is_pending_and_takedown_requires_the_token(client):
    submitted = client.post(
        "/api/board/submit",
        json={
            "name": "<script>Ada</script> Ochieng",
            "role": "Junior Backend Engineer",
            "pitch": "FastAPI and PostgreSQL builder looking for a first backend role.",
            "link": "https://github.com/ada-ochieng",
        },
    )
    assert submitted.status_code == 200

    data = submitted.json()
    assert data["status"] == "pending"
    assert data["takedown_token"]
    entry_id = data["id"]

    public_ids = {entry["id"] for entry in client.get("/api/board").json()}
    assert entry_id not in public_ids

    assert (
        client.post(
            "/api/board/takedown",
            json={"id": entry_id, "token": "wrong-token-value"},
        ).status_code
        == 403
    )
    removed = client.post(
        "/api/board/takedown",
        json={"id": entry_id, "token": data["takedown_token"]},
    )
    assert removed.status_code == 200
    assert removed.json()["removed"] is True
    assert entry_id not in {entry["id"] for entry in client.get("/api/board").json()}


def test_board_rejects_non_https_links(client):
    response = client.post(
        "/api/board/submit",
        json={
            "name": "Test User",
            "role": "Frontend Developer",
            "pitch": "I build accessible Vue interfaces and want peer visibility.",
            "link": "http://example.com/profile",
        },
    )
    assert response.status_code == 422


def test_admin_can_approve_pending_board_entry(client):
    submitted = client.post(
        "/api/board/submit",
        json={
            "name": "Njeri Wambui",
            "role": "Data Analyst",
            "pitch": "SQL and Python analyst open to junior data roles in Nairobi.",
            "link": "https://github.com/njeri-wambui",
        },
    ).json()
    entry_id = submitted["id"]

    assert (
        client.post(f"/api/admin/board/{entry_id}/approve").status_code == 401
    )
    assert (
        client.post(
            f"/api/admin/board/{entry_id}/approve",
            headers={"X-Admin-Key": "wrong-key"},
        ).status_code
        == 401
    )

    approved = client.post(
        f"/api/admin/board/{entry_id}/approve",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    public = client.get("/api/board").json()
    assert any(entry["id"] == entry_id and entry["name"] == "Njeri Wambui" for entry in public)


def test_events_are_allowlisted_and_admin_stats_aggregate(client):
    for name in ("page_view", "cv_open", "match_run", "booking_start", "lab_attempt"):
        response = client.post("/api/events", json={"name": name, "session": "sess-123"})
        assert response.status_code == 204
        assert response.content == b""

    assert (
        client.post(
            "/api/events", json={"name": "raw_jd_dump", "session": "sess-123"}
        ).status_code
        == 422
    )

    assert client.get("/api/admin/stats").status_code == 401
    stats = client.get(
        "/api/admin/stats", headers={"X-Admin-Key": "test-admin-key"}
    )
    assert stats.status_code == 200

    data = stats.json()
    assert data["events"] == {
        "page_view": 1,
        "cv_open": 1,
        "match_run": 1,
        "booking_start": 1,
        "lab_attempt": 1,
    }
    assert data["total_events"] == 5
    assert data["total_bookings"] == 0
    assert "total_attempts" in data["redteam"]
    assert data["board"]["approved"] == 2
    assert "takedown" not in stats.text.lower()


def test_apply_analyze_raw_jd_creates_tracked_job(client, fake_match):
    response = client.post(
        "/api/apply/analyze",
        json={
            "raw_jd": (
                "We need a backend engineer with Python, FastAPI, PostgreSQL, "
                "payment integrations, and Docker experience."
            )
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["job_id"]
    assert data["score"] == 78
    assert data["matched"] == ["Python", "FastAPI", "PostgreSQL"]
    assert data["gaps"] == ["Docker"]
    assert data["citations"][0]["project_title"] == "AyuTech Motors"

    jobs = client.get("/api/apply/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == data["job_id"]
    assert jobs[0]["status"] == "saved"

    updated = client.put(
        f"/api/apply/jobs/{data['job_id']}", json={"status": "applied"}
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "applied"
    assert client.get("/api/apply/jobs").json()[0]["status"] == "applied"


def test_apply_draft_is_grounded_and_never_auto_submits(client, fake_match):
    analyzed = client.post(
        "/api/apply/analyze",
        json={
            "raw_jd": (
                "Backend role: Python, FastAPI, PostgreSQL, APIs, and payments. "
                "You will build reliable services and work with a product team."
            )
        },
    ).json()

    response = client.post("/api/apply/draft", json={"job_id": analyzed["job_id"]})
    assert response.status_code == 200

    data = response.json()
    assert data["human_review_required"] is True
    assert data["auto_submit"] is False
    assert len(data["bullet_tips"]) == 3
    assert "Karatina University" in data["cover_letter"]
    assert "Judiciary of Kenya" in data["cover_letter"]
    assert "AyuTech Motors" in data["cover_letter"]
    assert "Find Wachira a Job" in data["cover_letter"]
    assert data["citations"][0]["project_slug"] == "ayutech"
    assert data["status"] == "drafted"
    assert client.get("/api/apply/jobs").json()[0]["status"] == "drafted"


def test_apply_draft_unknown_job_returns_404(client, fake_match):
    response = client.post("/api/apply/draft", json={"job_id": "missing-job"})
    assert response.status_code == 404
