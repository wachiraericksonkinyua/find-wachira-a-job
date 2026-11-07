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
import logging
import os
import re
import secrets
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, StringConstraints, field_validator
from typing_extensions import Annotated

from app.bookings import get_bookings
from app.embeddings import _connect_postgres
from app.redteam import security_report

BOARD_STATE_FILE = Path(__file__).with_name("board_state.json")
logger = logging.getLogger(__name__)
_lock = threading.Lock()
_pg_retry_after = 0.0

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS board_submissions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        pitch TEXT NOT NULL,
        link TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        takedown_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analytics_events (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        session TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS board_submissions_status_idx ON board_submissions (status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS analytics_events_name_idx ON analytics_events (name, created_at DESC)",
]

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


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _with_pg_schema() -> Any | None:
    global _pg_retry_after

    if time.monotonic() < _pg_retry_after:
        return None
    connection = _connect_postgres()
    if connection is None:
        _pg_retry_after = time.monotonic() + 30
        return None
    try:
        with connection.cursor() as cursor:
            for statement in _SCHEMA_STATEMENTS:
                cursor.execute(statement)
            for entry in SEED_ENTRIES:
                cursor.execute(
                    "INSERT INTO board_submissions "
                    "(id, name, role, pitch, link, status, takedown_hash, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO NOTHING",
                    (
                        entry["id"],
                        entry["name"],
                        entry["role"],
                        entry["pitch"],
                        entry["link"],
                        entry["status"],
                        entry["takedown_hash"],
                        entry["created_at"],
                    ),
                )
        _pg_retry_after = 0.0
        return connection
    except Exception as exc:
        logger.warning("Could not prepare board tables (%s).", exc)
        _pg_retry_after = time.monotonic() + 30
        connection.close()
        return None


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


def _admin_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        **_public_entry(entry),
        "status": str(entry.get("status", "pending")),
        "created_at": _iso(entry.get("created_at")),
    }


def list_approved() -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT id, name, role, pitch, link FROM board_submissions "
                    "WHERE status = 'approved' ORDER BY name ASC"
                )
                rows = cursor.fetchall()
            return [_public_entry(row) for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL board read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_state()
        entries = [
            _public_entry(entry)
            for entry in state["entries"]
            if isinstance(entry, dict) and entry.get("status") == "approved"
        ]
    entries.sort(key=lambda entry: entry["name"].lower())
    return entries


def admin_entries(status: str | None = None) -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                if status:
                    cursor.execute(
                        "SELECT id, name, role, pitch, link, status, created_at "
                        "FROM board_submissions WHERE status = %s "
                        "ORDER BY created_at DESC",
                        (status,),
                    )
                else:
                    cursor.execute(
                        "SELECT id, name, role, pitch, link, status, created_at "
                        "FROM board_submissions ORDER BY created_at DESC"
                    )
                rows = cursor.fetchall()
            return [_admin_entry(row) for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL admin board read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_state()
        entries = [
            _admin_entry(entry)
            for entry in state["entries"]
            if isinstance(entry, dict) and (not status or entry.get("status") == status)
        ]
    entries.sort(key=lambda entry: entry.get("created_at") or "", reverse=True)
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

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO board_submissions "
                    "(id, name, role, pitch, link, status, takedown_hash, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        entry["id"],
                        entry["name"],
                        entry["role"],
                        entry["pitch"],
                        entry["link"],
                        entry["status"],
                        entry["takedown_hash"],
                        entry["created_at"],
                    ),
                )
            return {
                "id": entry["id"],
                "status": entry["status"],
                "takedown_token": token,
                "message": "Profile submitted for review. Keep the takedown token private.",
            }
        except Exception as exc:
            logger.warning("PostgreSQL board insert failed (%s).", exc)
        finally:
            connection.close()

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
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT takedown_hash FROM board_submissions WHERE id = %s",
                    (entry_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise KeyError(entry_id)
                if not secrets.compare_digest(str(row[0]), _hash_token(token)):
                    raise PermissionError("Invalid takedown token")
                cursor.execute(
                    "DELETE FROM board_submissions WHERE id = %s", (entry_id,)
                )
            return {"removed": True, "id": entry_id}
        except (KeyError, PermissionError):
            raise
        except Exception as exc:
            logger.warning("PostgreSQL board takedown failed (%s).", exc)
        finally:
            connection.close()

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
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "UPDATE board_submissions SET status = 'approved' "
                    "WHERE id = %s RETURNING id, name, role, pitch, link, status, created_at",
                    (entry_id,),
                )
                row = cursor.fetchone()
            if row is None:
                raise KeyError(entry_id)
            return {
                "id": entry_id,
                "status": "approved",
                "entry": _public_entry(row),
            }
        except KeyError:
            raise
        except Exception as exc:
            logger.warning("PostgreSQL board approval failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_state()
        for entry in state["entries"]:
            if not isinstance(entry, dict) or entry.get("id") != entry_id:
                continue
            entry["status"] = "approved"
            _save_state(state)
            return {"id": entry_id, "status": "approved", "entry": _public_entry(entry)}
        raise KeyError(entry_id)


def reject_entry(entry_id: str) -> dict[str, Any]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE board_submissions SET status = 'rejected' WHERE id = %s",
                    (entry_id,),
                )
                if cursor.rowcount == 0:
                    raise KeyError(entry_id)
            return {"id": entry_id, "status": "rejected"}
        except KeyError:
            raise
        except Exception as exc:
            logger.warning("PostgreSQL board rejection failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_state()
        for entry in state["entries"]:
            if isinstance(entry, dict) and entry.get("id") == entry_id:
                entry["status"] = "rejected"
                _save_state(state)
                return {"id": entry_id, "status": "rejected"}
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

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO analytics_events (name, session, created_at) "
                    "VALUES (%s, %s, %s)",
                    (event["name"], event["session"], event["created_at"]),
                )
            return
        except Exception as exc:
            logger.warning("PostgreSQL analytics insert failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_state()
        state["event_counts"][payload.name] = (
            int(state["event_counts"].get(payload.name, 0)) + 1
        )
        state["recent_events"].append(event)
        state["recent_events"] = state["recent_events"][-500:]
        _save_state(state)


def _event_counts() -> dict[str, int]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT name, COUNT(*) FROM analytics_events GROUP BY name"
                )
                rows = cursor.fetchall()
            counts = {name: 0 for name in EVENT_NAMES}
            for name, total in rows:
                if name in counts:
                    counts[str(name)] = int(total)
            return counts
        except Exception as exc:
            logger.warning("PostgreSQL analytics read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        return dict(_load_state()["event_counts"])


def admin_stats() -> dict[str, Any]:
    counts = _event_counts()
    entries = admin_entries(status=None)
    approved = sum(1 for entry in entries if entry.get("status") == "approved")
    pending = sum(1 for entry in entries if entry.get("status") == "pending")

    total_bookings = len(get_bookings())
    redteam_stats = security_report()
    return {
        "events": counts,
        "total_events": sum(counts.values()),
        "total_bookings": total_bookings,
        "bookings": total_bookings,
        "board": {
            "approved": approved,
            "pending": pending,
            "total": len(entries),
        },
        "redteam": redteam_stats,
        "redteam_stats": redteam_stats,
    }
