"""Static guards that keep credentials out of the repository.

Runs as a dedicated, dependency-free CI job (standard library + pytest only),
so it stays fast and cannot be skipped because of an unrelated import error.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Runtime state and local secrets that must never be committed.
PROTECTED_FILES = (
    "backend/.env",
    "backend/app/bookings.json",
    "backend/app/pet_state.json",
    "backend/app/redteam_state.json",
    "backend/app/board_state.json",
    "backend/app/apply_jobs.json",
)

# Only real-looking credentials are matched. Documentation placeholders are
# filtered separately below.
SECRET_PATTERNS = {
    "Groq API key": re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "Postgres URL with inline credentials": re.compile(
        r"postgres(?:ql)?://[^\s:/@]+:[^\s@]+@"
    ),
}

# Obvious placeholders such as the ones in .env.example or docs.
PLACEHOLDER = re.compile(
    r"(password|passwd|changeme|example|placeholder|your[_-]?\w*|<[^>]+>)",
    re.IGNORECASE,
)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _tracked_files() -> list[str]:
    return [line for line in _git("ls-files").splitlines() if line]


def test_sensitive_runtime_files_are_not_tracked():
    tracked = set(_tracked_files())
    leaked = [path for path in PROTECTED_FILES if path in tracked]
    assert not leaked, f"Sensitive files are tracked by git: {leaked}"


def test_sensitive_runtime_files_are_gitignored():
    for path in PROTECTED_FILES:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=REPO_ROOT,
        )
        assert result.returncode == 0, f"{path} is not ignored by .gitignore"


def test_no_secret_patterns_in_tracked_files():
    findings: list[str] = []

    for path in _tracked_files():
        try:
            text = (REPO_ROOT / path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for label, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(text):
                if PLACEHOLDER.search(match.group(0)):
                    continue
                findings.append(f"{path}: possible {label}")

    assert not findings, "Possible secrets in tracked files:\n" + "\n".join(findings)
