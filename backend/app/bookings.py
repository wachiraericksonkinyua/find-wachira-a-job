"""Interview bookings and pet-lead capture with optional PostgreSQL storage."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.embeddings import _connect_postgres
from app.pet import load_state

logger = logging.getLogger(__name__)

BOOKINGS_FILE = Path(__file__).with_name("bookings.json")
_lock = threading.Lock()

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        name TEXT NOT NULL,
        company TEXT,
        contact TEXT NOT NULL,
        role TEXT,
        preferred_time TEXT,
        message TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pet_leads (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        type TEXT NOT NULL,
        note TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS bookings_created_at_idx ON bookings (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS pet_leads_created_at_idx ON pet_leads (created_at DESC)",
]


class BookingRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    company: str | None = Field(default=None, max_length=120)
    contact: str = Field(min_length=3, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    preferred_time: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "name", "company", "contact", "role", "preferred_time", "message",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json_bookings() -> list[dict[str, Any]]:
    if not BOOKINGS_FILE.exists():
        return []
    try:
        data = json.loads(BOOKINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _save_json_bookings(bookings: list[dict[str, Any]]) -> None:
    BOOKINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(
        dir=BOOKINGS_FILE.parent, prefix=f".{BOOKINGS_FILE.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(bookings, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, BOOKINGS_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _with_pg_schema() -> Any | None:
    connection = _connect_postgres()
    if connection is None:
        return None
    try:
        with connection.cursor() as cursor:
            for statement in _SCHEMA_STATEMENTS:
                cursor.execute(statement)
        return connection
    except Exception as exc:
        logger.warning("Could not prepare booking tables (%s).", exc)
        connection.close()
        return None


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def save_booking(payload: BookingRequest) -> dict[str, Any]:
    booking = {
        "id": str(uuid.uuid4()),
        "created_at": _now(),
        **payload.model_dump(),
    }

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO bookings "
                    "(id, created_at, name, company, contact, role, preferred_time, message) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        booking["id"],
                        booking["created_at"],
                        booking["name"],
                        booking["company"],
                        booking["contact"],
                        booking["role"],
                        booking["preferred_time"],
                        booking["message"],
                    ),
                )
        except Exception as exc:
            logger.warning("PostgreSQL booking insert failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        bookings = _load_json_bookings()
        bookings.append(booking)
        _save_json_bookings(bookings)

    return booking


def record_pet_lead(action_type: str, note: str | None) -> None:
    lead = {"created_at": _now(), "type": action_type, "note": note}

    connection = _with_pg_schema()
    if connection is None:
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO pet_leads (created_at, type, note) VALUES (%s, %s, %s)",
                (lead["created_at"], lead["type"], lead["note"]),
            )
    except Exception as exc:
        logger.warning("PostgreSQL pet lead insert failed (%s).", exc)
    finally:
        connection.close()


def get_bookings() -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT id, created_at, name, company, contact, role, "
                    "preferred_time, message FROM bookings "
                    "ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()
            return [{**row, "created_at": _iso(row["created_at"])} for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL bookings read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        return list(reversed(_load_json_bookings()))


def get_pet_leads() -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT id, created_at, type, note FROM pet_leads "
                    "ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()
            return [{**row, "created_at": _iso(row["created_at"])} for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL pet leads read failed (%s).", exc)
        finally:
            connection.close()

    interactions = load_state().get("interactions", [])
    return list(reversed(interactions))
