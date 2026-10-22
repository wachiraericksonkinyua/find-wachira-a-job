from __future__ import annotations

import json
import threading
from pathlib import Path

from fpdf import FPDF

DATA_FILE = Path(__file__).with_name("resume_data.json")

# The PDF only changes when resume_data.json changes, so cache the rendered
# bytes and invalidate on mtime instead of rebuilding on every request.
_cache: tuple[float, bytes] | None = None
_lock = threading.Lock()

NAVY = (16, 42, 67)
ACCENT = (0, 122, 204)
MUTED = (90, 100, 110)
BODY = (34, 40, 49)


def load_resume_data() -> dict:
    """Read the structured source of truth (safe to expose as JSON)."""
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


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
    """Return a cached, deterministic PDF built from resume_data.json."""
    global _cache

    mtime = DATA_FILE.stat().st_mtime
    with _lock:
        if _cache and _cache[0] == mtime:
            return _cache[1]

    pdf_bytes = _build_pdf(load_resume_data())

    with _lock:
        _cache = (mtime, pdf_bytes)
    return pdf_bytes
