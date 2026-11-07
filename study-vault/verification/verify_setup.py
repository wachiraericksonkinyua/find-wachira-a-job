#!/usr/bin/env python3
"""Verification harness for the Find Wachira a Job study vault.

Checks:
1. Backend dependencies + `pytest -q`.
2. Frontend dependencies + `npm test -- --run`.
3. SSRF validator blocks loopback / localhost / cloud metadata.
4. Admin auth uses timing-safe `secrets.compare_digest`.

Run from the repository root:

    python study-vault/verification/verify_setup.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
WEB_DIR = REPO_ROOT / "web"
BACKEND_VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"

SSRF_TARGETS = (
    "http://127.0.0.1",
    "http://localhost",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/internal",
    "file:///etc/passwd",
)


def _tail(text: str, lines: int = 8) -> str:
    cleaned = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(cleaned[-lines:]) if cleaned else "(no output)"


def _report(name: str, passed: bool, detail: str = "") -> bool:
    marker = "PASS" if passed else "FAIL"
    print(f"[{marker}] {name}")
    if detail:
        for line in detail.splitlines():
            print(f"       {line}")
    return passed


def run_command(name: str, command: list[str], cwd: Path, timeout: int) -> bool:
    if shutil.which(command[0]) is None and not Path(command[0]).exists():
        return _report(name, False, f"command not found: {command[0]}")
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _report(name, False, f"timed out after {timeout}s")
    except OSError as exc:
        return _report(name, False, str(exc))

    passed = result.returncode == 0
    output = (result.stdout or "") + (result.stderr or "")
    detail = _tail(output, 6) if not passed else _tail(result.stdout, 2)
    return _report(name, passed, detail)


def check_backend_tests() -> bool:
    python = str(BACKEND_VENV_PYTHON) if BACKEND_VENV_PYTHON.exists() else sys.executable
    return run_command(
        "Backend dependencies + pytest",
        [python, "-m", "pytest", "-q"],
        BACKEND_DIR,
        timeout=240,
    )


def check_frontend_tests() -> bool:
    node_modules = WEB_DIR / "node_modules"
    if not node_modules.exists():
        return _report(
            "Frontend dependencies + npm test",
            False,
            "web/node_modules is missing. Run: cd web && npm install",
        )
    return run_command(
        "Frontend dependencies + npm test",
        ["npm", "test", "--", "--run"],
        WEB_DIR,
        timeout=300,
    )


def check_ssrf_validator() -> bool:
    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from app.apply_assistant import validate_public_url
    except Exception as exc:  # noqa: BLE001 - report any import failure clearly
        return _report("SSRF validator blocks private targets", False, str(exc))

    failures: list[str] = []
    for target in SSRF_TARGETS:
        try:
            validate_public_url(target)
        except ValueError:
            continue
        except Exception as exc:  # noqa: BLE001 - unexpected failure is still a failure
            failures.append(f"{target} -> unexpected {type(exc).__name__}: {exc}")
        else:
            failures.append(f"{target} -> was allowed")

    detail = "\n".join(failures) if failures else f"blocked {len(SSRF_TARGETS)} unsafe targets"
    return _report("SSRF validator blocks private targets", not failures, detail)


def check_timing_safe_auth() -> bool:
    main_source = BACKEND_DIR / "app" / "main.py"
    try:
        source = main_source.read_text(encoding="utf-8")
    except OSError as exc:
        return _report("Timing-safe admin auth", False, str(exc))

    if "secrets.compare_digest" not in source:
        return _report(
            "Timing-safe admin auth",
            False,
            "backend/app/main.py does not call secrets.compare_digest",
        )

    sys.path.insert(0, str(BACKEND_DIR))
    try:
        from fastapi import HTTPException

        from app.main import require_admin_key
    except Exception as exc:  # noqa: BLE001
        return _report("Timing-safe admin auth", False, str(exc))

    os.environ["ADMIN_API_KEY"] = "study-vault-verification-key"
    try:
        require_admin_key("wrong-key")
    except HTTPException as exc:
        if exc.status_code != 401:
            return _report(
                "Timing-safe admin auth",
                False,
                f"wrong key returned HTTP {exc.status_code}, expected 401",
            )
    except Exception as exc:  # noqa: BLE001
        return _report("Timing-safe admin auth", False, str(exc))
    else:
        return _report("Timing-safe admin auth", False, "wrong key was accepted")

    try:
        require_admin_key("study-vault-verification-key")
    except Exception as exc:  # noqa: BLE001
        return _report("Timing-safe admin auth", False, str(exc))

    return _report(
        "Timing-safe admin auth",
        True,
        "secrets.compare_digest present; wrong key → 401; correct key accepted",
    )


def maybe_reexec_in_backend_venv() -> None:
    """Use backend/.venv when available so FastAPI imports work."""
    if not BACKEND_VENV_PYTHON.exists():
        return
    try:
        current = Path(sys.executable).resolve()
        target = BACKEND_VENV_PYTHON.resolve()
    except OSError:
        return
    if current == target:
        return
    os.execv(str(target), [str(target), str(Path(__file__).resolve()), *sys.argv[1:]])


def main() -> int:
    maybe_reexec_in_backend_venv()

    print("Find Wachira a Job — Study Vault Verification")
    print(f"Repository: {REPO_ROOT}")
    print("-" * 58)

    results = [
        check_backend_tests(),
        check_frontend_tests(),
        check_ssrf_validator(),
        check_timing_safe_auth(),
    ]

    print("-" * 58)
    passed = sum(1 for result in results if result)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")

    if passed == total:
        print("Study vault is ready. Open study-vault/README.md and start reading.")
        return 0

    print("Fix the failed checks above, then run this script again.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
