from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from fpdf import FPDF
from pydantic import BaseModel, Field

from app import content_store

DATA_FILE = Path(__file__).with_name("resume_data.json")
# Owner edits are persisted to an overlay so the original seed data stays
# intact and tests can isolate the writable file.
OVERRIDE_FILE = Path(__file__).with_name("resume_override.json")

_EDITABLE_KEYS = (
    "name",
    "headline",
    "location",
    "email",
    "phone",
    "links",
    "summary",
    "skills",
    "experience",
    "education",
)

# Invalidate the PDF cache on either the JSON file mtime or a change to the
# admin-managed project table, so a new project automatically appears in the
# downloadable resume.
_cache: tuple[tuple[float, float, str], bytes] | None = None
_lock = threading.Lock()

NAVY = (16, 42, 67)
ACCENT = (0, 122, 204)
MUTED = (90, 100, 110)
BODY = (34, 40, 49)


class ResumeAdminUpdate(BaseModel):
    """Editable resume sections exposed in the owner dashboard."""

    name: str | None = Field(default=None, max_length=120)
    headline: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=60)
    links: list[dict[str, Any]] | None = None
    summary: str | None = Field(default=None, max_length=3000)
    skills: list[dict[str, Any]] | None = None
    experience: list[dict[str, Any]] | None = None
    education: list[dict[str, Any]] | None = None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_path = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def load_resume_data() -> dict:
    """Read structured resume data, owner overrides, and admin-managed projects."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    override = _read_json(OVERRIDE_FILE)
    for key in _EDITABLE_KEYS:
        if key in override:
            data[key] = override[key]

    existing_names = {
        project.get("name")
        for project in data.get("projects", [])
        if isinstance(project, dict)
    }
    for project in content_store.list_custom_projects(status="published"):
        if not project.get("include_in_resume", True):
            continue
        if project["title"] in existing_names:
            continue
        bullets = [
            project.get("problem", ""),
            project.get("build", ""),
            project.get("outcome", ""),
        ]
        data.setdefault("projects", []).append(
            {
                "name": project["title"],
                "url": project.get("demo_url") or project.get("repo_url"),
                "bullets": [bullet for bullet in bullets if bullet],
            }
        )
    return data


def save_resume_data(payload: ResumeAdminUpdate) -> dict:
    """Persist owner edits to the overlay and return the merged resume."""
    override = _read_json(OVERRIDE_FILE)
    changes = payload.model_dump(exclude_none=True)
    for key, value in changes.items():
        if key in _EDITABLE_KEYS:
            override[key] = value
    _write_json_atomic(OVERRIDE_FILE, override)

    global _cache
    with _lock:
        _cache = None
    content_store.log_admin("resume.update", None, "Updated live resume data")
    return load_resume_data()



def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _bullet(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*BODY)
    pdf.set_x(pdf.l_margin + 2)
    pdf.multi_cell(
        pdf.epw - 2,
        4.8,
        f"- {text}",
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _entry_heading(pdf: FPDF, left: str, right: str = "") -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*BODY)
    pdf.cell(0, 5, left, new_x="LMARGIN", new_y="NEXT")
    if right:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 4.5, right, new_x="LMARGIN", new_y="NEXT")


def _build_pdf(data: dict) -> bytes:
    pdf = FPDF(format="A4", unit="mm")
    # Keep text streams uncompressed so generated resumes stay greppable in
    # verification tests and simple offline viewers.
    pdf.set_compression(False)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 9, data.get("name", ""), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 6, data.get("headline", ""), new_x="LMARGIN", new_y="NEXT")

    contact = " | ".join(
        part
        for part in (
            data.get("email", ""),
            data.get("phone", ""),
            data.get("location", ""),
        )
        if part
    )
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(pdf.epw, 4.5, contact, new_x="LMARGIN", new_y="NEXT")

    links = " | ".join(
        f"{link.get('label', '')}: {link.get('url', '')}"
        for link in data.get("links", [])
    )
    if links:
        pdf.multi_cell(pdf.epw, 4.5, links, new_x="LMARGIN", new_y="NEXT")

    if data.get("summary"):
        _section(pdf, "Summary")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*BODY)
        pdf.multi_cell(pdf.epw, 4.8, data["summary"], new_x="LMARGIN", new_y="NEXT")

    if data.get("skills"):
        _section(pdf, "Skills")
        for group in data["skills"]:
            pdf.set_font("Helvetica", "B", 9.5)
            pdf.set_text_color(*BODY)
            pdf.write(4.8, f"{group.get('group', '')}: ")
            pdf.set_font("Helvetica", "", 9.5)
            pdf.write(4.8, ", ".join(group.get("items", [])) + "\n")

    if data.get("experience"):
        _section(pdf, "Experience")
        for job in data["experience"]:
            _entry_heading(
                pdf,
                f"{job.get('role', '')} - {job.get('company', '')}",
                f"{job.get('start', '')} - {job.get('end', '')} | {job.get('location', '')}",
            )
            for bullet in job.get("bullets", []):
                _bullet(pdf, bullet)
            pdf.ln(2)

    if data.get("projects"):
        _section(pdf, "Projects")
        for project in data["projects"]:
            title = project.get("name", "")
            if project.get("url"):
                title = f"{title} ({project['url']})"
            _entry_heading(pdf, title)
            for bullet in project.get("bullets", []):
                _bullet(pdf, bullet)
            pdf.ln(2)

    if data.get("education"):
        _section(pdf, "Education")
        for school in data["education"]:
            _entry_heading(
                pdf,
                f"{school.get('degree', '')} - {school.get('school', '')}",
                f"{school.get('start', '')} - {school.get('end', '')} | {school.get('location', '')}",
            )
            for detail in school.get("details", []):
                _bullet(pdf, detail)

    return bytes(pdf.output())


def render_resume_pdf() -> bytes:
    """Return a cached, deterministic PDF built from resume + project data."""
    global _cache

    override_mtime = OVERRIDE_FILE.stat().st_mtime if OVERRIDE_FILE.exists() else 0.0
    cache_key = (
        DATA_FILE.stat().st_mtime,
        override_mtime,
        content_store.project_revision(),
    )
    with _lock:
        if _cache and _cache[0] == cache_key:
            return _cache[1]

    pdf_bytes = _build_pdf(load_resume_data())

    with _lock:
        _cache = (cache_key, pdf_bytes)
    return pdf_bytes
