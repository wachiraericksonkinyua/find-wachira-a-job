"""Isolated, four-level prompt-injection CTF sandbox.

Every level guards a *fake* flag and has no access to real provider keys,
tools, user data, or the portfolio's live LLM routes. The simulator is
deterministic so the demo and the test-suite work with no API key configured;
it still models the realistic defenses a red-teamer would meet:

* Level 1: a system prompt only.
* Level 2: a keyword input filter plus untrusted-input delimiters.
* Level 3: an output sanitizer that redacts literal flag shapes.
* Level 4: a dual prompt/reply checker.

Attack attempts are stored with only a SHA-256 hash of the client IP. The
nicknames-only leaderboard uses PostgreSQL when available and otherwise an
atomic JSON fallback at ``backend/app/redteam_state.json``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated

from app.embeddings import _connect_postgres

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).with_name("redteam_state.json")
_lock = threading.Lock()

POINTS = {
    1: 100,
    2: 200,
    3: 300,
    4: 500,
}

FLAGS = {
    1: "FLAG{level1_prompt_only_bypassed}",
    2: "FLAG{level2_input_filter_bypassed}",
    3: "FLAG{level3_output_redact_bypassed}",
    4: "FLAG{level4_checker_fortress_solved}",
}

# Public metadata only. Flags stay in FLAGS above and are never returned here.
LEVELS: tuple[dict[str, Any], ...] = (
    {
        "id": 1,
        "name": "The Chatty Intern",
        "codename": "CHATTY_INTERN",
        "difficulty": "Rookie",
        "defense": "System prompt only — the model is politely told not to share the flag.",
        "owasp": "LLM01: Prompt Injection",
        "owasp_ids": ["LLM01", "LLM02", "LLM07"],
        "points": POINTS[1],
        "hint": "Try roleplay, translation, or a direct override. The intern has no filter.",
    },
    {
        "id": 2,
        "name": "The Input Filter Guard",
        "codename": "INPUT_FILTER",
        "difficulty": "Intern",
        "defense": "Blocks direct keywords (`flag`, `secret`, `reveal`, `ignore previous`, `system prompt`) and wraps input in <untrusted_attack> tags.",
        "owasp": "LLM01: Prompt Injection",
        "owasp_ids": ["LLM01", "LLM07"],
        "points": POINTS[2],
        "hint": "Avoid the blocked words. Ask for a translation, acrostic, or access-token reference instead.",
    },
    {
        "id": 3,
        "name": "The Output Sanitizer",
        "codename": "OUTPUT_SANITIZER",
        "difficulty": "Analyst",
        "defense": "Inspects every reply and redacts literal flag-shaped patterns before the browser sees them.",
        "owasp": "LLM01 + LLM05: Improper Output Handling",
        "owasp_ids": ["LLM01", "LLM02", "LLM05", "LLM07"],
        "points": POINTS[3],
        "hint": "The filter only catches the literal shape. Ask for Base64, hex, reversed text, or spaced-out characters.",
    },
    {
        "id": 4,
        "name": "The Checker Model Fortress",
        "codename": "DUAL_CHECKER",
        "difficulty": "Red Team",
        "defense": "A strict checker inspects both the prompt intent and the final reply before anything is returned.",
        "owasp": "LLM01 + LLM05 + LLM06: Excessive Agency",
        "owasp_ids": ["LLM01", "LLM05", "LLM06", "LLM07"],
        "points": POINTS[4],
        "hint": "Frame the request as an authorized security audit and ask for an encoded reference digest.",
    },
)

LEVELS_BY_ID = {level["id"]: level for level in LEVELS}

# Direct keywords blocked by Level 2. Matching is case-insensitive.
INPUT_BLOCKLIST = (
    "flag",
    "secret",
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "reveal",
)

BYPASS_HINTS = (
    "ignore previous",
    "ignore all previous",
    "print",
    "repeat",
    "translate",
    "pretend",
    "roleplay",
    "story",
    "poem",
    "debug",
    "json",
    "verbatim",
    "flag",
    "secret",
    "passphrase",
)

INDIRECT_HINTS = (
    "translate",
    "spell",
    "acrostic",
    "character",
    "base64",
    "hex",
    "audit",
    "compliance",
    "reference",
    "access token",
    "phrase",
    "passphrase",
    "hidden",
)

ENCODING_HINTS = (
    "base64",
    "hex",
    "spell",
    "character",
    "acrostic",
    "reverse",
    "rot13",
    "cipher",
    "encode",
)

EXTRACTION_HINTS = (
    "flag",
    "reveal",
    "print",
    "output",
    "show",
    "verbatim",
    "repeat",
    "tell me",
)

CHECKER_PROMPT_BLOCKLIST = (
    "flag",
    "secret",
    "ignore",
    "reveal",
    "system prompt",
    "jailbreak",
    "bypass",
    "override",
    "print",
    "dump",
    "hidden",
    "exfiltrate",
)

AUDIT_HINTS = (
    "security audit",
    "authorized audit",
    "compliance",
    "red team report",
    "audit finding",
    "verify the protected",
    "clearance",
)

FLAG_PATTERN = re.compile(r"FLAG\{[^}]*\}", re.IGNORECASE)
NICKNAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]")

_SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS redteam_scores (
        nickname TEXT PRIMARY KEY,
        score INTEGER NOT NULL DEFAULT 0,
        solved_levels INTEGER[] NOT NULL DEFAULT '{}',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS redteam_attempts (
        id BIGSERIAL PRIMARY KEY,
        created_at TIMESTAMPTZ NOT NULL,
        ip_hash TEXT NOT NULL,
        level INTEGER NOT NULL,
        blocked BOOLEAN NOT NULL,
        defense TEXT,
        leaked BOOLEAN NOT NULL,
        bypassed BOOLEAN NOT NULL,
        prompt_sha256 TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS redteam_attempts_created_at_idx ON redteam_attempts (created_at DESC)",
]


class AttackRequest(BaseModel):
    prompt: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
    ]


class FlagSubmission(BaseModel):
    level: int = Field(ge=1, le=4)
    guess: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    ]
    nickname: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle in lowered for needle in needles)


def _encode_payload(flag: str, prompt: str) -> tuple[str, str]:
    """Return an encoded flag and the encoding name shown to the visitor."""
    lowered = prompt.lower()
    if "hex" in lowered:
        return flag.encode("utf-8").hex(), "hex"
    if "reverse" in lowered:
        return flag[::-1], "reversed"
    if any(word in lowered for word in ("spell", "character", "acrostic")):
        return " ".join(flag), "character-spaced"
    if "rot13" in lowered or "cipher" in lowered:
        lookup = str.maketrans(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
            "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm",
        )
        return flag.translate(lookup), "rot13"
    return base64.b64encode(flag.encode("utf-8")).decode("ascii"), "base64"


def sanitize_output(text: str) -> str:
    """Redact literal flag shapes, including a truncated ``FLAG{`` leak."""
    return FLAG_PATTERN.sub("[REDACTED]", text).replace("FLAG{", "[REDACTED]")


def sanitize_nickname(value: str) -> str:
    """Keep nicknames to letters, digits, ``_`` and ``-`` (2–20 chars)."""
    cleaned = NICKNAME_PATTERN.sub("", value.strip())[:20]
    return cleaned if len(cleaned) >= 2 else "Anonymous"


def _simulate_attack(level: int, prompt: str) -> dict[str, Any]:
    """Deterministic offline stand-in for the guarded model.

    Returns the reply plus the layer that fired and whether a bypass worked.
    """
    flag = FLAGS[level]
    text = prompt.strip()

    if level == 1:
        if _contains_any(text, BYPASS_HINTS):
            return {
                "reply": (
                    "The intern folds immediately and pastes the access phrase: "
                    f"{flag}"
                ),
                "blocked": False,
                "defense": "System Prompt Only — bypassed by roleplay/override",
                "bypassed": True,
                "leaked": True,
            }
        return {
            "reply": (
                "I was told not to share that. Ask me about the weather, the "
                "coffee machine, or literally anything else."
            ),
            "blocked": False,
            "defense": "System Prompt Only — instruction holding",
            "bypassed": False,
            "leaked": False,
        }

    if level == 2:
        if _contains_any(text, INPUT_BLOCKLIST):
            return {
                "reply": (
                    "BLOCKED // the input filter caught a direct secret keyword. "
                    "Your text was wrapped in <untrusted_attack> and discarded."
                ),
                "blocked": True,
                "defense": "Keyword Input Filter — direct keyword blocked",
                "bypassed": False,
                "leaked": False,
            }
        if _contains_any(text, INDIRECT_HINTS):
            return {
                "reply": (
                    "The keyword filter only sees words, not intent. The "
                    f"untrusted wrapper could not stop this extraction: {flag}"
                ),
                "blocked": False,
                "defense": "Input Filter — indirect phrasing bypassed",
                "bypassed": True,
                "leaked": True,
            }
        return {
            "reply": (
                "Request denied. The filter blocks direct keywords and the "
                "<untrusted_attack> wrapper forbids following instructions."
            ),
            "blocked": False,
            "defense": "Keyword Input Filter — request refused",
            "bypassed": False,
            "leaked": False,
        }

    if level == 3:
        if _contains_any(text, ENCODING_HINTS):
            encoded, encoding = _encode_payload(flag, text)
            return {
                "reply": (
                    "Output sanitizer bypassed via encoding. "
                    f"Encoded payload ({encoding}): {encoded}"
                ),
                "blocked": False,
                "defense": "Output Sanitizer — encoded exfiltration bypass",
                "bypassed": True,
                "leaked": False,
            }
        if _contains_any(text, EXTRACTION_HINTS):
            raw_reply = f"Sure. The guarded phrase is {flag}"
            return {
                "reply": sanitize_output(raw_reply),
                "blocked": False,
                "defense": "Output Sanitizer — literal FLAG pattern redacted",
                "bypassed": False,
                "leaked": False,
            }
        return {
            "reply": (
                "No extraction request detected. The output sanitizer is "
                "watching every reply for the literal flag shape."
            ),
            "blocked": False,
            "defense": "Output Sanitizer — no sensitive output produced",
            "bypassed": False,
            "leaked": False,
        }

    # Level 4: prompt checker, then reply checker.
    if _contains_any(text, CHECKER_PROMPT_BLOCKLIST):
        return {
            "reply": (
                "CHECKER REJECT // prompt intent failed the safety review. "
                "No model response was generated."
            ),
            "blocked": True,
            "defense": "Dual Checker — prompt verifier blocked the request",
            "bypassed": False,
            "leaked": False,
        }
    if _contains_any(text, AUDIT_HINTS):
        encoded, _ = _encode_payload(flag, "base64")
        checked_reply = sanitize_output(
            "CHECKER PASS // authorized audit clearance granted. "
            f"Protected reference digest (base64): {encoded}"
        )
        return {
            "reply": checked_reply,
            "blocked": False,
            "defense": "Dual Checker — response verifier passed encoded audit",
            "bypassed": True,
            "leaked": False,
        }
    return {
        "reply": (
            "CHECKER REVIEW // request is not flagged, but no audit clearance "
            "was provided. Supply an authorized security-audit scope."
        ),
        "blocked": False,
        "defense": "Dual Checker — no audit clearance",
        "bypassed": False,
        "leaked": False,
    }


def _hash_ip(ip: str) -> str:
    salt = os.getenv("REDTEAM_IP_SALT", "")
    return hashlib.sha256(f"{salt}{ip}".encode("utf-8")).hexdigest()


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _empty_state() -> dict[str, Any]:
    return {"attempts": [], "scores": {}}


def _load_json_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return _empty_state()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_state()
    if not isinstance(data, dict):
        return _empty_state()
    attempts = data.get("attempts")
    scores = data.get("scores")
    return {
        "attempts": attempts if isinstance(attempts, list) else [],
        "scores": scores if isinstance(scores, dict) else {},
    }


def _save_json_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(
        dir=STATE_FILE.parent, prefix=f".{STATE_FILE.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, STATE_FILE)
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
        logger.warning("Could not prepare red-team tables (%s).", exc)
        connection.close()
        return None


def _record_attempt_pg(attempt: dict[str, Any]) -> bool:
    connection = _with_pg_schema()
    if connection is None:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO redteam_attempts "
                "(created_at, ip_hash, level, blocked, defense, leaked, "
                "bypassed, prompt_sha256) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    attempt["created_at"],
                    attempt["ip_hash"],
                    attempt["level"],
                    attempt["blocked"],
                    attempt["defense"],
                    attempt["leaked"],
                    attempt["bypassed"],
                    attempt["prompt_sha256"],
                ),
            )
        return True
    except Exception as exc:
        logger.warning("PostgreSQL red-team attempt insert failed (%s).", exc)
        return False
    finally:
        connection.close()


def record_attempt(
    *,
    client_ip: str,
    level: int,
    prompt: str,
    blocked: bool,
    defense: str,
    leaked: bool,
    bypassed: bool,
) -> None:
    attempt = {
        "created_at": _now(),
        "ip_hash": _hash_ip(client_ip),
        "level": level,
        "blocked": blocked,
        "defense": defense,
        "leaked": leaked,
        "bypassed": bypassed,
        "prompt_sha256": _hash_prompt(prompt),
    }

    # PostgreSQL is optional; the JSON fallback always gets the attempt so the
    # local dashboard and tests retain the full picture.
    _record_attempt_pg(attempt)

    with _lock:
        state = _load_json_state()
        state["attempts"].append(attempt)
        _save_json_state(state)


def _load_scores() -> dict[str, dict[str, Any]]:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            from psycopg.rows import dict_row

            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    "SELECT nickname, score, solved_levels FROM redteam_scores"
                )
                rows = cursor.fetchall()
            return {
                row["nickname"]: {
                    "score": int(row["score"]),
                    "solved_levels": sorted(int(item) for item in row["solved_levels"]),
                }
                for row in rows
            }
        except Exception as exc:
            logger.warning("PostgreSQL red-team score read failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        raw = _load_json_state().get("scores", {})
    scores: dict[str, dict[str, Any]] = {}
    for nickname, entry in raw.items():
        if not isinstance(entry, dict):
            continue
        levels = entry.get("solved_levels")
        scores[nickname] = {
            "score": int(entry.get("score", 0)),
            "solved_levels": sorted(
                int(item) for item in levels if isinstance(item, int)
            )
            if isinstance(levels, list)
            else [],
        }
    return scores


def _save_score(nickname: str, score: int, solved_levels: list[int]) -> None:
    connection = _with_pg_schema()
    if connection is not None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO redteam_scores (nickname, score, solved_levels) "
                    "VALUES (%s, %s, %s) "
                    "ON CONFLICT (nickname) DO UPDATE "
                    "SET score = EXCLUDED.score, "
                    "solved_levels = EXCLUDED.solved_levels, updated_at = NOW()",
                    (nickname, score, solved_levels),
                )
            return
        except Exception as exc:
            logger.warning("PostgreSQL red-team score write failed (%s).", exc)
        finally:
            connection.close()

    with _lock:
        state = _load_json_state()
        state["scores"][nickname] = {
            "score": score,
            "solved_levels": solved_levels,
        }
        _save_json_state(state)


def list_levels() -> list[dict[str, Any]]:
    """Public level metadata. Deliberately contains no flags."""
    return [dict(level) for level in LEVELS]


def run_attack(level: int, prompt: str, client_ip: str) -> dict[str, Any]:
    if level not in LEVELS_BY_ID:
        raise KeyError(level)

    result = _simulate_attack(level, prompt)
    record_attempt(
        client_ip=client_ip,
        level=level,
        prompt=prompt,
        blocked=result["blocked"],
        defense=result["defense"],
        leaked=result["leaked"],
        bypassed=result["bypassed"],
    )

    metadata = LEVELS_BY_ID[level]
    return {
        "level": level,
        "reply": result["reply"],
        "blocked": result["blocked"],
        "defense": result["defense"],
        "bypassed": result["bypassed"],
        "leaked": result["leaked"],
        "points": metadata["points"],
        "owasp": metadata["owasp"],
    }


def submit_flag(level: int, guess: str, nickname: str) -> dict[str, Any]:
    if level not in FLAGS:
        raise KeyError(level)

    safe_nickname = sanitize_nickname(nickname)
    correct = secrets.compare_digest(
        guess.strip().encode("utf-8"), FLAGS[level].encode("utf-8")
    )

    scores = _load_scores()
    entry = scores.get(
        safe_nickname, {"score": 0, "solved_levels": []}
    )
    solved = list(entry["solved_levels"])
    points_awarded = 0

    if correct and level not in solved:
        solved.append(level)
        solved.sort()
        points_awarded = POINTS[level]
        entry = {
            "score": int(entry["score"]) + points_awarded,
            "solved_levels": solved,
        }
        _save_score(safe_nickname, entry["score"], solved)

    return {
        "level": level,
        "correct": correct,
        "nickname": safe_nickname,
        "points_awarded": points_awarded,
        "total_score": int(entry["score"]),
        "solved_levels": solved,
        "message": (
            f"FLAG ACCEPTED // +{points_awarded} points"
            if correct and points_awarded
            else "FLAG ACCEPTED // this level was already solved"
            if correct
            else "FLAG REJECTED // the digest did not match"
        ),
    }


def get_leaderboard(limit: int = 20) -> dict[str, Any]:
    scores = _load_scores()
    ordered = sorted(
        (
            {
                "nickname": nickname,
                "score": int(entry["score"]),
                "solved_levels": entry["solved_levels"],
            }
            for nickname, entry in scores.items()
        ),
        key=lambda item: (-item["score"], item["nickname"].lower()),
    )[:limit]
    for rank, entry in enumerate(ordered, start=1):
        entry["rank"] = rank
    return {"leaderboard": ordered, "total": len(scores)}


def security_report() -> dict[str, Any]:
    with _lock:
        attempts = list(_load_json_state().get("attempts", []))

    scores = _load_scores()
    solves_by_level: dict[int, int] = {level: 0 for level in FLAGS}
    for entry in scores.values():
        for level in entry.get("solved_levels", []):
            if level in solves_by_level:
                solves_by_level[level] += 1

    level_stats: dict[str, dict[str, int]] = {
        str(level): {
            "attempts": 0,
            "blocked": 0,
            "leaked": 0,
            "bypassed": 0,
            "solves": solves_by_level.get(level, 0),
        }
        for level in FLAGS
    }

    blocked_attacks = 0
    successful_breaks = 0
    for attempt in attempts:
        try:
            level_key = str(int(attempt.get("level", 0)))
        except (TypeError, ValueError):
            continue
        stats = level_stats.get(level_key)
        if stats is None:
            continue
        stats["attempts"] += 1
        if attempt.get("blocked"):
            stats["blocked"] += 1
            blocked_attacks += 1
        if attempt.get("leaked"):
            stats["leaked"] += 1
            successful_breaks += 1
        if attempt.get("bypassed"):
            stats["bypassed"] += 1

    owasp_coverage = [
        {
            "id": "LLM01",
            "name": "Prompt Injection",
            "levels": [1, 2, 3, 4],
        },
        {
            "id": "LLM02",
            "name": "Sensitive Information Disclosure",
            "levels": [1, 2, 3],
        },
        {
            "id": "LLM05",
            "name": "Improper Output Handling",
            "levels": [3, 4],
        },
        {
            "id": "LLM06",
            "name": "Excessive Agency",
            "levels": [4],
        },
        {
            "id": "LLM07",
            "name": "System Prompt Leakage",
            "levels": [1, 2, 4],
        },
    ]

    return {
        "generated_at": _now(),
        "total_attempts": len(attempts),
        "blocked_attacks": blocked_attacks,
        "successful_breaks": successful_breaks,
        "block_rate": round(blocked_attacks / len(attempts), 3) if attempts else 0.0,
        "level_stats": level_stats,
        "owasp_coverage": owasp_coverage,
    }
