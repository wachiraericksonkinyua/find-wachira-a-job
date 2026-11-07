"""Shared test isolation.

Tests must never touch a live Supabase/PostgreSQL instance. Individual tests
can still opt in by monkeypatching these variables back in.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_live_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DIRECT_URL", "")
    yield
