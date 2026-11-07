"""Admin-managed portfolio projects with resume/RAG propagation."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated

from app import content_store

_TAG_PATTERN = re.compile(r"<[^>]+>")
_CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


def _clean_text(value: Any) -> Any:
    if isinstance(value, str):
        value = _CONTROL_PATTERN.sub(" ", value)
        value = _TAG_PATTERN.sub("", value)
        return re.sub(r"\s+", " ", value).strip()
    return value


def _validate_optional_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Links must be valid http:// or https:// URLs.")
    if parsed.username or parsed.password:
        raise ValueError("Links must not contain credentials.")
    return value.strip()


class ProjectAdminCreate(BaseModel):
    title: Annotated[str, Field(min_length=3, max_length=120)]
    problem: Annotated[str, Field(min_length=10, max_length=2000)]
    build: Annotated[str, Field(min_length=10, max_length=4000)]
    outcome: Annotated[str, Field(min_length=5, max_length=2000)]
    stack: list[str] = Field(default_factory=list, max_length=20)
    repo_url: str | None = Field(default=None, max_length=500)
    demo_url: str | None = Field(default=None, max_length=500)

    @field_validator("title", "problem", "build", "outcome", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        return _clean_text(value)

    @field_validator("stack", mode="before")
    @classmethod
    def split_stack(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("stack")
    @classmethod
    def clean_stack(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            item = _clean_text(item)[:40]
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned[:20]

    @field_validator("repo_url", "demo_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return _validate_optional_url(value)


class ProjectReaction(BaseModel):
    reaction: str = Field(pattern="^(heart|roast)$")


class ProjectAdminUpdate(BaseModel):
    title: Annotated[str | None, Field(default=None, min_length=3, max_length=120)]
    problem: Annotated[str | None, Field(default=None, min_length=10, max_length=2000)]
    build: Annotated[str | None, Field(default=None, min_length=10, max_length=4000)]
    outcome: Annotated[str | None, Field(default=None, min_length=5, max_length=2000)]
    stack: list[str] | None = Field(default=None, max_length=20)
    repo_url: str | None = Field(default=None, max_length=500)
    demo_url: str | None = Field(default=None, max_length=500)

    @field_validator("title", "problem", "build", "outcome", mode="before")
    @classmethod
    def clean_text(cls, value: Any) -> Any:
        return _clean_text(value)

    @field_validator("stack", mode="before")
    @classmethod
    def split_stack(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("stack")
    @classmethod
    def clean_stack(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            item = _clean_text(item)[:40]
            if item and item not in cleaned:
                cleaned.append(item)
        return cleaned[:20]

    @field_validator("repo_url", "demo_url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return _validate_optional_url(value)


def list_admin_projects() -> list[dict[str, Any]]:
    return content_store.list_custom_projects(status=None)


def create_project(payload: ProjectAdminCreate) -> dict[str, Any]:
    project = content_store.create_custom_project(
        title=payload.title,
        problem=payload.problem,
        build=payload.build,
        outcome=payload.outcome,
        stack=payload.stack,
        repo_url=payload.repo_url,
        demo_url=payload.demo_url,
    )
    content_store.log_admin(
        "project.create", project["id"], f"Added project: {project['title']}"
    )
    return project


def update_project(
    project_id: str, payload: ProjectAdminUpdate
) -> dict[str, Any]:
    changes = payload.model_dump(exclude_none=True)
    project = content_store.update_custom_project(project_id, **changes)
    content_store.log_admin(
        "project.update", project_id, f"Updated project: {project['title']}"
    )
    return project


def delete_project(project_id: str) -> bool:
    deleted = content_store.delete_custom_project(project_id)
    if deleted:
        content_store.log_admin("project.delete", project_id, "Removed project")
    return deleted
