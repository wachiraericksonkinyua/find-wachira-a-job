"""Anonymous, moderated Roast Wall submissions."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, StringConstraints, field_validator
from typing_extensions import Annotated

from app import content_store

_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        value = _CONTROL_PATTERN.sub(" ", value)
        value = _TAG_PATTERN.sub("", value)
        return re.sub(r"\s+", " ", value).strip()
    return value


class RoastSubmission(BaseModel):
    text: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=5, max_length=280)
    ]
    advice: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=3, max_length=280),
        ]
        | None
    ) = None
    target: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, max_length=80),
        ]
        | None
    ) = None

    @field_validator("text", "advice", "target", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        return _clean(value)


class RoastModeration(BaseModel):
    note: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=240)
    ] = ""


def submit_roast(payload: RoastSubmission) -> dict[str, Any]:
    roast = content_store.create_roast(payload.text, payload.advice, payload.target)
    return {
        "id": roast["id"],
        "status": roast["status"],
        "message": "Sent to the moderation queue! Once Erickson approves it, it goes live on the wall.",
    }


def public_roasts() -> list[dict[str, Any]]:
    return [
        {
            "id": roast["id"],
            "author": "@anonymous_dev",
            "target": roast.get("target"),
            "text": roast["text"],
            "advice": roast["advice"],
            "created_at": roast["created_at"],
        }
        for roast in content_store.list_roasts(status="approved")
    ]


def admin_roasts(status: str | None = None) -> list[dict[str, Any]]:
    return content_store.list_roasts(status=status or None)


def approve_roast(roast_id: str, note: str = "") -> dict[str, Any]:
    roast = content_store.moderate_roast(roast_id, "approved", note or None)
    content_store.log_admin("roast.approve", roast_id, note or "approved")
    return roast


def reject_roast(roast_id: str, note: str = "") -> dict[str, Any]:
    roast = content_store.moderate_roast(roast_id, "rejected", note or None)
    content_store.log_admin("roast.reject", roast_id, note or "rejected")
    return roast


def delete_roast(roast_id: str) -> bool:
    deleted = content_store.delete_roast(roast_id)
    if deleted:
        content_store.log_admin("roast.delete", roast_id, "removed by owner")
    return deleted
