"""Persistent content store for roasts, portfolio projects, reactions, and logs.

Uses Supabase/PostgreSQL when a database URL is configured, with atomic JSON
files as the zero-config offline fallback. This keeps the local demo working
without credentials while persisting real content in production.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROASTS_FILE = Path(__file__).with_name("roast_wall.json")
PROJECTS_FILE = Path(__file__).with_name("custom_projects.json")
REACTIONS_FILE = Path(__file__).with_name("project_reactions.json")
LOGS_FILE = Path(__file__).with_name("admin_logs.json")
_lock = threading.Lock()
_pg_retry_after = 0.0

ROAST_STATUSES = ("pending", "approved", "rejected")
REACTION_TYPES = ("heart", "roast")

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS roast_wall (
        id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        advice TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL,
        moderated_at TIMESTAMPTZ,
        moderation_note TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_projects (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        problem TEXT NOT NULL,
        build TEXT NOT NULL,
        outcome TEXT NOT NULL,
        stack TEXT NOT NULL DEFAULT '[]',
        repo_url TEXT,
        demo_url TEXT,
        status TEXT NOT NULL DEFAULT 'published',
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS project_reactions (
        id BIGSERIAL PRIMARY KEY,
        project_id TEXT NOT NULL,
        reaction TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_audit_log (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        target TEXT,
        detail TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS roast_wall_status_idx ON roast_wall (status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS project_reactions_project_idx ON project_reactions (project_id, reaction)",
    "CREATE INDEX IF NOT EXISTS admin_audit_log_created_idx ON admin_audit_log (created_at DESC)",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _with_pg_schema() -> Any | None:
    global _pg_retry_after

    if time.monotonic() < _pg_retry_after:
        return None

    # Imported lazily to avoid a circular import:
    # embeddings -> projects -> content_store -> embeddings.
    from app.embeddings import _connect_postgres

    connection = _connect_postgres()
    if connection is None:
        _pg_retry_after = time.monotonic() + 30
        return None
    try:
        with connection.cursor() as cursor:
            for statement in _SCHEMA_STATEMENTS:
                cursor.execute(statement)
        _pg_retry_after = 0.0
        return connection
    except Exception as exc:
        logger.warning("Could not prepare content tables (%s).", exc)
        _pg_retry_after = time.monotonic() + 30
        connection.close()
        return None


def _load_json_list(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    items = data.get(key)
    return items if isinstance(items, list) else []


def _save_json_list(path: Path, key: str, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({key: items}, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _roast_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "text": str(row["text"]),
        "advice": row.get("advice"),
        "status": str(row.get("status", "pending")),
        "created_at": _iso(row.get("created_at")),
        "moderated_at": _iso(row.get("moderated_at")),
        "moderation_note": row.get("moderation_note"),
    }


def create_roast(text: str, advice: str | None = None) -> dict[str, Any]:
    roast = {
        "id": uuid.uuid4().hex,
        "text": text,
        "advice": advice,
        "status": "pending",
        "created_at": _now(),
        "moderated_at": None,
        "moderation_note": None,
    }

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO roast_wall "
                    "(id, text, advice, status, created_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        roast["id"],
                        roast["text"],
                        roast["advice"],
                        roast["status"],
                        roast["created_at"],
                    ),
                )
            return dict(roast)
        except Exception as exc:
            logger.warning("PostgreSQL roast insert failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        roasts = _load_json_list(ROASTS_FILE, "roasts")
        roasts.append(roast)
        _save_json_list(ROASTS_FILE, "roasts", roasts)
    return dict(roast)


def list_roasts(status: str | None = None) -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                if status:
                    cursor.execute(
                        "SELECT * FROM roast_wall WHERE status = %s "
                        "ORDER BY created_at DESC",
                        (status,),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM roast_wall ORDER BY created_at DESC"
                    )
                rows = cursor.fetchall()
            return [_roast_row(row) for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL roast read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        roasts = list(_load_json_list(ROASTS_FILE, "roasts"))
    if status:
        roasts = [roast for roast in roasts if roast.get("status") == status]
    roasts.sort(key=lambda roast: roast.get("created_at") or "", reverse=True)
    return roasts


def moderate_roast(roast_id: str, status: str, note: str | None = None) -> dict[str, Any]:
    if status not in ROAST_STATUSES:
        raise ValueError("Unknown roast moderation status.")
    moderated_at = _now()

    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "UPDATE roast_wall SET status = %s, moderated_at = %s, "
                    "moderation_note = %s WHERE id = %s RETURNING *",
                    (status, moderated_at, note, roast_id),
                )
                row = cursor.fetchone()
            if row is None:
                raise KeyError(roast_id)
            return _roast_row(row)
        except KeyError:
            raise
        except Exception as exc:
            logger.warning("PostgreSQL roast moderation failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        roasts = _load_json_list(ROASTS_FILE, "roasts")
        for roast in roasts:
            if roast.get("id") == roast_id:
                roast["status"] = status
                roast["moderated_at"] = moderated_at
                roast["moderation_note"] = note
                _save_json_list(ROASTS_FILE, "roasts", roasts)
                return dict(roast)
    raise KeyError(roast_id)


def delete_roast(roast_id: str) -> bool:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM roast_wall WHERE id = %s", (roast_id,))
                deleted = cursor.rowcount > 0
            if deleted:
                return True
        except Exception as exc:
            logger.warning("PostgreSQL roast delete failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        roasts = _load_json_list(ROASTS_FILE, "roasts")
        remaining = [roast for roast in roasts if roast.get("id") != roast_id]
        if len(remaining) == len(roasts):
            return False
        _save_json_list(ROASTS_FILE, "roasts", remaining)
        return True


def _project_row(row: dict[str, Any]) -> dict[str, Any]:
    stack = row.get("stack") or []
    if isinstance(stack, str):
        try:
            stack = json.loads(stack)
        except json.JSONDecodeError:
            stack = []
    return {
        "id": str(row["id"]),
        "title": str(row["title"]),
        "problem": str(row["problem"]),
        "build": str(row["build"]),
        "outcome": str(row["outcome"]),
        "stack": stack if isinstance(stack, list) else [],
        "repo_url": row.get("repo_url"),
        "demo_url": row.get("demo_url"),
        "status": str(row.get("status", "published")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "custom": True,
    }


def list_custom_projects(status: str | None = "published") -> list[dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                if status:
                    cursor.execute(
                        "SELECT * FROM portfolio_projects WHERE status = %s "
                        "ORDER BY created_at DESC",
                        (status,),
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM portfolio_projects ORDER BY created_at DESC"
                    )
                rows = cursor.fetchall()
            return [_project_row(row) for row in rows]
        except Exception as exc:
            logger.warning("PostgreSQL project read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        projects = list(_load_json_list(PROJECTS_FILE, "projects"))
    if status:
        projects = [project for project in projects if project.get("status") == status]
    projects.sort(key=lambda project: project.get("created_at") or "", reverse=True)
    for project in projects:
        project["custom"] = True
    return projects


def create_custom_project(
    *,
    title: str,
    problem: str,
    build: str,
    outcome: str,
    stack: list[str],
    repo_url: str | None,
    demo_url: str | None,
) -> dict[str, Any]:
    now = _now()
    project = {
        "id": uuid.uuid4().hex,
        "title": title,
        "problem": problem,
        "build": build,
        "outcome": outcome,
        "stack": stack,
        "repo_url": repo_url,
        "demo_url": demo_url,
        "status": "published",
        "created_at": now,
        "updated_at": now,
        "custom": True,
    }

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO portfolio_projects "
                    "(id, title, problem, build, outcome, stack, repo_url, "
                    "demo_url, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        project["id"],
                        project["title"],
                        project["problem"],
                        project["build"],
                        project["outcome"],
                        json.dumps(stack),
                        repo_url,
                        demo_url,
                        project["status"],
                        now,
                        now,
                    ),
                )
            return dict(project)
        except Exception as exc:
            logger.warning("PostgreSQL project insert failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        projects = _load_json_list(PROJECTS_FILE, "projects")
        projects.append(project)
        _save_json_list(PROJECTS_FILE, "projects", projects)
    return dict(project)


def update_custom_project(project_id: str, **changes: Any) -> dict[str, Any]:
    allowed = {"title", "problem", "build", "outcome", "stack", "repo_url", "demo_url"}
    updates = {key: value for key, value in changes.items() if key in allowed}
    if not updates:
        return _get_custom_project(project_id)
    updates["updated_at"] = _now()

    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            assignments = []
            values: list[Any] = []
            for key, value in updates.items():
                assignments.append(f"{key} = %s")
                values.append(json.dumps(value) if key == "stack" else value)
            values.append(project_id)
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    f"UPDATE portfolio_projects SET {', '.join(assignments)} "
                    "WHERE id = %s RETURNING *",
                    tuple(values),
                )
                row = cursor.fetchone()
            if row is None:
                raise KeyError(project_id)
            return _project_row(row)
        except KeyError:
            raise
        except Exception as exc:
            logger.warning("PostgreSQL project update failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        projects = _load_json_list(PROJECTS_FILE, "projects")
        for project in projects:
            if project.get("id") == project_id:
                project.update(updates)
                project["custom"] = True
                _save_json_list(PROJECTS_FILE, "projects", projects)
                return project
    raise KeyError(project_id)


def _get_custom_project(project_id: str) -> dict[str, Any]:
    for project in list_custom_projects(status=None):
        if project.get("id") == project_id:
            return project
    raise KeyError(project_id)


def delete_custom_project(project_id: str) -> bool:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM portfolio_projects WHERE id = %s", (project_id,)
                )
                deleted = cursor.rowcount > 0
            if deleted:
                return True
        except Exception as exc:
            logger.warning("PostgreSQL project delete failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        projects = _load_json_list(PROJECTS_FILE, "projects")
        remaining = [project for project in projects if project.get("id") != project_id]
        if len(remaining) == len(projects):
            return False
        _save_json_list(PROJECTS_FILE, "projects", remaining)
        return True


def project_revision() -> str:
    """Cheap cache key for resume PDF invalidation when projects change."""
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*), COALESCE(MAX(updated_at)::text, '') "
                    "FROM portfolio_projects"
                )
                row = cursor.fetchone()
            return f"{row[0]}:{row[1]}"
        except Exception as exc:
            logger.warning("PostgreSQL project revision failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        projects = _load_json_list(PROJECTS_FILE, "projects")
    latest = max((str(p.get("updated_at", "")) for p in projects), default="")
    return f"{len(projects)}:{latest}"


def record_reaction(project_id: str, reaction: str) -> dict[str, int]:
    if reaction not in REACTION_TYPES:
        raise ValueError("Unknown project reaction.")
    created_at = _now()

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO project_reactions (project_id, reaction, created_at) "
                    "VALUES (%s, %s, %s)",
                    (project_id, reaction, created_at),
                )
        except Exception as exc:
            logger.warning("PostgreSQL reaction insert failed (%s).", exc)
        finally:
            connection.close()
        return reaction_counts().get(project_id, {"heart": 0, "roast": 0})

    with _lock:
        reactions = _load_json_list(REACTIONS_FILE, "reactions")
        reactions.append(
            {
                "project_id": project_id,
                "reaction": reaction,
                "created_at": created_at,
            }
        )
        _save_json_list(REACTIONS_FILE, "reactions", reactions)
    counts = {"heart": 0, "roast": 0}
    for item in reactions:
        if item.get("project_id") == project_id and item.get("reaction") in counts:
            counts[item["reaction"]] += 1
    return counts


def reaction_counts() -> dict[str, dict[str, int]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT project_id, reaction, COUNT(*) "
                    "FROM project_reactions GROUP BY project_id, reaction"
                )
                rows = cursor.fetchall()
            counts: dict[str, dict[str, int]] = {}
            for project_id, reaction, total in rows:
                counts.setdefault(str(project_id), {"heart": 0, "roast": 0})
                if reaction in REACTION_TYPES:
                    counts[str(project_id)][reaction] = int(total)
            return counts
        except Exception as exc:
            logger.warning("PostgreSQL reaction read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        reactions = _load_json_list(REACTIONS_FILE, "reactions")
    counts = {}
    for item in reactions:
        project_id = str(item.get("project_id", ""))
        reaction = item.get("reaction")
        if not project_id or reaction not in REACTION_TYPES:
            continue
        counts.setdefault(project_id, {"heart": 0, "roast": 0})
        counts[project_id][reaction] += 1
    return counts


def log_admin(action: str, target: str | None = None, detail: str | None = None) -> None:
    entry = {
        "created_at": _now(),
        "actor": "owner",
        "action": action,
        "target": target,
        "detail": detail,
    }

    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO admin_audit_log "
                    "(created_at, actor, action, target, detail) VALUES (%s, %s, %s, %s, %s)",
                    (
                        entry["created_at"],
                        entry["actor"],
                        entry["action"],
                        entry["target"],
                        entry["detail"],
                    ),
                )
        except Exception as exc:
            logger.warning("PostgreSQL audit log insert failed (%s).", exc)
        finally:
            connection.close()
        return

    with _lock:
        logs = _load_json_list(LOGS_FILE, "logs")
        logs.append(entry)
        logs = logs[-500:]
        _save_json_list(LOGS_FILE, "logs", logs)


def list_admin_logs(limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT * FROM admin_audit_log ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                rows = cursor.fetchall()
            return [
                {
                    "id": row.get("id"),
                    "created_at": _iso(row.get("created_at")),
                    "actor": row.get("actor"),
                    "action": row.get("action"),
                    "target": row.get("target"),
                    "detail": row.get("detail"),
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("PostgreSQL audit log read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        logs = list(_load_json_list(LOGS_FILE, "logs"))
    logs = list(reversed(logs))[:limit]
    return logs
