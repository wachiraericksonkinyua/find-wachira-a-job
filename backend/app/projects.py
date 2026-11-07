import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, Field

from app import content_store


class Project(BaseModel):
    id: str
    title: str
    problem: str
    build: str
    outcome: str
    stack: list[str]
    repo_url: str | None = None
    demo_url: str | None = None
    custom: bool = False
    reactions: dict[str, int] = Field(default_factory=lambda: {"heart": 0, "roast": 0})


class ProjectChunk(TypedDict):
    project_id: str
    chunk_type: str
    content: str
    hash: str


def load_projects() -> list[Project]:
    path = Path(__file__).parent / "projects_data.json"
    with open(path, "r", encoding="utf-8") as f:
        base_projects = [Project(**item) for item in json.load(f)]

    custom_projects = [
        Project(**item) for item in content_store.list_custom_projects(status="published")
    ]
    merged = base_projects + custom_projects

    counts = content_store.reaction_counts()
    for project in merged:
        project.reactions = counts.get(project.id, {"heart": 0, "roast": 0})
    return merged


def get_project(project_id: str) -> Project | None:
    for project in load_projects():
        if project.id == project_id:
            return project
    return None


def iter_project_chunks() -> Iterator[ProjectChunk]:
    for p in load_projects():
        for chunk_type in ("problem", "build", "outcome"):
            # The title travels with every chunk so it makes sense alone.
            content = f"{p.title} ({chunk_type}): {getattr(p, chunk_type)}"
            digest = hashlib.sha256(
                f"{p.id}:{chunk_type}:{content}".encode("utf-8")
            ).hexdigest()
            yield {
                "project_id": p.id,
                "chunk_type": chunk_type,
                "content": content,
                "hash": digest,
            }