from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
import json
import re
import threading

from pydantic import BaseModel, Field, field_validator, model_validator

#state_file tells other devs rhat this is a vvariable that is a file path to the pet state json file. 
#__file__ is a special variable in Python that represents the path of the current script. The with_name method is used to create a new Path object with the same directory as the current script but with a different file name, in this case, "pet_state.json". This means that STATE_FILE will point to a file named "pet_state.json" located in the same directory as the script that contains this code.
#.with_name("pet_state.json") swaps pet.py for pet_state.json, so the path is the same as the current file but with a different name. 
STATE_FILE = Path(__file__).with_name("pet_state.json")
_lock = threading.Lock()#the _ is a polit warning ro otherfiles"only use this variable inside pet.py"
#threading.lock creates a digital bathroom keey -onluy one rquest can hold the key and edit the file at a time stopping  2 request rom scrambling your json

RELIEF_POINTS = {
    "link":     5,
    "lead": 8,
    "intro": 12,
    "know_person": 12,
    "book": 20,
}

# Types where the note may contain a person's details. We refuse emails here
# so recruiters never hand us a third party's private address.
PRIVATE_NOTE_TYPES = {"intro", "know_person"}
# Types that are useless without a short note (a link with no link).
NOTE_REQUIRED_TYPES = {"link", "lead", "intro", "know_person"}

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

QUIPS = {
    "link": "A link? Saving my dignity one URL at a time.",
    "lead": "A lead! I can already smell the free office coffee.",
    "intro": "An introduction? My LinkedIn is crying with joy.",
    "know_person": "So you know someone. Name-dropping absolutely works on me.",
    "book": "An interview booked?! I'm putting on my good tie.",
}


class InteractRequest(BaseModel):
    """Shape of POST /api/pet/interact. FastAPI rejects bad bodies with 422."""

    type: Literal["link", "lead", "intro", "know_person", "book"]
    note: str | None = Field(default=None, max_length=280)

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str | None) -> str | None:
        # Trim whitespace and treat "" as no note at all.
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def check_note_rules(self):
        if self.type in NOTE_REQUIRED_TYPES and not self.note:
            raise ValueError(f"A note is required for '{self.type}'.")
        if self.type in PRIVATE_NOTE_TYPES and self.note:
            if EMAIL_RE.search(self.note):
                raise ValueError(
                    "No third-party emails, please. Drop a name or a profile link instead."
                )
        return self


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value):
    try:
        return datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def _seed_state() -> dict:
    """Fresh demo state: roughly matches the old 68% mock meter."""
    now = _now()
    return {
        "last_help_at": (now - timedelta(hours=12)).isoformat(),
        "last_interview_at": (now - timedelta(days=20)).isoformat(),
        "rejections": 5,
        "relief_today": 0,
        "relief_date": now.date().isoformat(),
    }


def _write_unlocked(state: dict) -> None:
    """Write atomically so a crash cannot leave half a JSON file."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _load_unlocked() -> dict:
    """Read state; caller must already hold the lock."""
    if not STATE_FILE.exists():
        state = _seed_state()
        _write_unlocked(state)
        return state

    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt file: reset instead of crashing the API.
        state = _seed_state()
        _write_unlocked(state)
        return state


def load_state() -> dict:
    with _lock:
        return _load_unlocked()


def save_state(state: dict) -> None:
    with _lock:
        _write_unlocked(state)


def record_interaction(action_type: str, note: str | None) -> dict:
    """Apply relief + log the note, then return the fresh public state.

    Load-mutate-save happens inside one lock so two recruiters clicking at the
    same time cannot overwrite each other's points.
    """
    now = _now()

    with _lock:
        state = _load_unlocked()

        # Daily relief resets when the calendar day changes.
        if state.get("relief_date") != now.date().isoformat():
            state["relief_date"] = now.date().isoformat()
            state["relief_today"] = 0

        points = RELIEF_POINTS[action_type]
        state["relief_today"] = int(state.get("relief_today", 0)) + points
        state["last_help_at"] = now.isoformat()

        interactions = state.get("interactions", [])
        interactions.append(
            {"timestamp": now.isoformat(), "type": action_type, "note": note}
        )
        # Keep the log bounded so the JSON file cannot grow forever.
        state["interactions"] = interactions[-50:]

        _write_unlocked(state)

    return {
        **compute_state(state),
        "mood": "happy",
        "quip": QUIPS[action_type],
        "relief_gained": points,
        "interactions_logged": len(state["interactions"]),
    }


def _label(value: int) -> str:
    if value <= 25:
        return "Smug"
    if value <= 50:
        return "Hungry"
    if value <= 75:
        return "Starving"
    return "Crying in binary"


def _mood(value: int) -> str:
    """Map the meter to one of the monkey's three passive sprites.

    The backend owns this so every client (web, admin) shows the same mood.
    """
    if value > 75:
        return "anxious"
    if value > 25:
        return "smug"
    return "sleeping"


def compute_state(state: dict) -> dict:
    now = _now()
    last_help = _parse(state.get("last_help_at")) or now
    last_interview = _parse(state.get("last_interview_at")) or now

    hours_without_help = max(0.0, (now - last_help).total_seconds() / 3600)
    days_without_interview = max(0.0, (now - last_interview).total_seconds() / 86400)

    # Formula from the brief, each component capped independently.
    neglect = min(40, round(hours_without_help * 2))
    dry_spell = min(30, round(days_without_interview))
    rejections = min(20, max(0, int(state.get("rejections", 0))) * 2)

    relief_today = 0
    if state.get("relief_date") == now.date().isoformat():
        relief_today = max(0, int(state.get("relief_today", 0)))

    desperation = max(
        0,
        min(100, 10 + neglect + dry_spell + rejections - relief_today),
    )

    return {
        "desperation": desperation,
        "label": _label(desperation),
        "mood": _mood(desperation),
        "relief_today": relief_today,
        "components": {
            "base": 10,
            "neglect": neglect,
            "dry_spell": dry_spell,
            "rejections": rejections,
            "relief": relief_today,
        },
        "last_help_at": state.get("last_help_at"),
        "last_interview_at": state.get("last_interview_at"),
        "rejections": state.get("rejections", 0),
    }
