"""Curated peer Talent Board and anonymous funnel analytics.

The board is intentionally privacy-first: submissions are pending until an
admin approves them, public rows never include emails, and the submitter gets a
one-time takedown token whose hash (not the raw token) is stored.

Analytics store only allow-listed event names, a coarse session id, and a
timestamp. No raw job descriptions, emails, IP addresses, or free text are kept.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, StringConstraints, field_validator
from typing_extensions import Annotated

from app.bookings import get_bookings
from app.redteam import security_report

BOARD_STATE_FILE = Path(__file__).with_name("board_state.json")
_lock = threading.Lock()

EventName = Literal[
    "page_view",
    "cv_open",
    "match_run",
    "booking_start",
    "lab_attempt",
]
EVENT_NAMES: tuple[str, ...] = (
    "page_view",
    "cv_open",
    "match_run",
    "booking_start",
    "lab_attempt",
)

_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
_SESSION_PATTERN = re.compile(r"[^A-Za-z0-9_-]")

SEED_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "id": "sample-amina",
        "name": "Amina Otieno",
        "role": "Frontend Engineer",
        "pitch": (
            "Vue 3 and TypeScript developer building accessible dashboards. "
            "Open to junior frontend roles and paid internships in Nairobi."
        ),
        "link": "https://github.com/amina-dev",
        "status": "approved",
        "takedown_hash": "",
        "created_at": "2026-01-10T09:00:00+00:00",
    },
    {
        "id": "sample-brian",
        "name": "Brian Kimani",
        "role": "Backend Engineer (FastAPI)",
        "pitch": (
            "FastAPI, PostgreSQL, and Docker. I like clean APIs, tests, and "
            "shipping small improvements every week."
        ),
        "link": "https://github.com/brian-kimani",
        "status": "approved",
        "takedown_hash": "",
        "created_at": "2026-01-12T14:30:00+00:00",
    },
)


class BoardSubmission(BaseModel):
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)
    ]
    role: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)
    ]
    pitch: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=240)
    ]
    link: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=8, max_length=500)
    ]

    @field_validator("name", "role", "pitch", "link", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = _CONTROL_PATTERN.sub(" ", value)
            value = _TAG_PATTERN.sub("", value)
            return re.sub(r"\s+", " ", value).strip()
        return value

    @field_validator("link")
    @classmethod
    def https_only(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("link must be a public https:// URL")
        if parsed.username or parsed.password:
            raise ValueError("link must not contain credentials")
        if parsed.hostname and parsed.hostname.lower() in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("link must be a public https:// URL")
        return value


class TakedownRequest(BaseModel):
    id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    token: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=200)]


class EventRequest(BaseModel):
    name: EventName
    session: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_state() -> dict[str, Any]:
    return {
        "entries": [dict(entry) for entry in SEED_ENTRIES],
        "event_counts": {name: 0 for name in EVENT_NAMES},
        "recent_events": [],
    }


def _load_state() -> dict[str, Any]:
    if not BOARD_STATE_FILE.exists():
        return _empty_state()
    try:
        data = json.loads(BOARD_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()

    entries = data.get("entries")
    counts = data.get("event_counts")
    recent = data.get("recent_events")

    clean_counts = {name: 0 for name in EVENT_NAMES}
    if isinstance(counts, dict):
        for name in EVENT_NAMES:
            try:
                clean_counts[name] = max(0, int(counts.get(name, 0)))
            except (TypeError, ValueError):
                clean_counts[name] = 0

    return {
        "entries": entries if isinstance(entries, list) else [],
        "event_counts": clean_counts,
        "recent_events": recent if isinstance(recent, list) else [],
    }


def _save_state(state: dict[str, Any]) -> None:
    BOARD_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(
        dir=BOARD_STATE_FILE.parent,
        prefix=f".{BOARD_STATE_FILE.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, BOARD_STATE_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    # Vue escapes rendered text; the server only guarantees allow-listed fields.
    return {
        "id": str(entry.get("id", "")),
        "name": str(entry.get("name", "")),
        "role": str(entry.get("role", "")),
        "pitch": str(entry.get("pitch", "")),
        "link": str(entry.get("link", "")),
    }


def list_approved() -> list[dict[str, Any]]:
    with _lock:
        state = _load_state()
        entries = [
            _public_entry(entry)
            for entry in state["entries"]
            if isinstance(entry, dict) and entry.get("status") == "approved"
        ]
    entries.sort(key=lambda entry: entry["name"].lower())
    return entries


def submit_entry(payload: BoardSubmission) -> dict[str, Any]:
    token = secrets.token_urlsafe(24)
    entry = {
        "id": uuid.uuid4().hex,
        "name": payload.name,
        "role": payload.role,
        "pitch": payload.pitch,
        "link": payload.link,
        "status": "pending",
        "takedown_hash": _hash_token(token),
        "created_at": _now(),
    }

    with _lock:
        state = _load_state()
        state["entries"].append(entry)
        _save_state(state)

    return {
        "id": entry["id"],
        "status": entry["status"],
        "takedown_token": token,
        "message": "Profile submitted for review. Keep the takedown token private.",
    }


def takedown_entry(entry_id: str, token: str) -> dict[str, Any]:
    with _lock:
        state = _load_state()
        for index, entry in enumerate(state["entries"]):
            if not isinstance(entry, dict) or entry.get("id") != entry_id:
                continue
            expected = str(entry.get("takedown_hash", ""))
            if not expected or not secrets.compare_digest(
                expected, _hash_token(token)
            ):
                raise PermissionError("Invalid takedown token")
            state["entries"].pop(index)
            _save_state(state)
            return {"removed": True, "id": entry_id}
        raise KeyError(entry_id)


def approve_entry(entry_id: str) -> dict[str, Any]:
    with _lock:
        state = _load_state()
        for entry in state["entries"]:
            if not isinstance(entry, dict) or entry.get("id") != entry_id:
                continue
            entry["status"] = "approved"
            _save_state(state)
            return {"id": entry_id, "status": "approved", "entry": _public_entry(entry)}
        raise KeyError(entry_id)


def _clean_session(value: str) -> str:
    cleaned = _SESSION_PATTERN.sub("", value.strip())[:64]
    return cleaned or "anonymous"


def record_event(payload: EventRequest) -> None:
    """Persist only an allow-listed event name and a coarse session id."""
    event = {
        "name": payload.name,
        "session": _clean_session(payload.session),
        "created_at": _now(),
    }
    with _lock:
        state = _load_state()
        state["event_counts"][payload.name] = (
            int(state["event_counts"].get(payload.name, 0)) + 1
        )
        state["recent_events"].append(event)
        state["recent_events"] = state["recent_events"][-500:]
        _save_state(state)


def admin_stats() -> dict[str, Any]:
    with _lock:
        state = _load_state()
        counts = dict(state["event_counts"])
        entries = [entry for entry in state["entries"] if isinstance(entry, dict)]
        approved = sum(1 for entry in entries if entry.get("status") == "approved")
        pending = sum(1 for entry in entries if entry.get("status") == "pending")

    return {
        "events": counts,
        "total_events": sum(counts.values()),
        "total_bookings": len(get_bookings()),
        "board": {
            "approved": approved,
            "pending": pending,
            "total": len(entries),
        },
        "redteam": security_report(),
    }
