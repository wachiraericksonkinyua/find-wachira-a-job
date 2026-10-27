import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel


class Project(BaseModel):
    id: str
    title: str
    problem: str
    build: str
    outcome: str
    stack: list[str]


class ProjectChunk(TypedDict):
    project_id: str
    chunk_type: str
    content: str
    hash: str


def load_projects() -> list[Project]:
    path = Path(__file__).parent / "projects_data.json"
    with open(path, "r", encoding="utf-8") as f:
        return [Project(**item) for item in json.load(f)]


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