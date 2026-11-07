# Module 01 — Testing, Timing-Safe Auth, CI/CD, and CORS

**Days covered:** 16–20

## The one-sentence version

Test the API in memory with FastAPI `TestClient`, isolate tests with pytest
fixtures, compare secrets in constant time, run everything on every push with
GitHub Actions, and allow only known browser origins with CORS.

## Core concepts

### 1. Timing-safe secret comparison

`if supplied == expected` can behave differently depending on how many leading
characters match. An attacker who can measure timing may learn information about
the secret. `secrets.compare_digest()` is designed for constant-time comparison.

Why it matters here: the protected admin routes compare `X-Admin-Key` with
`ADMIN_API_KEY` using this function.

Repository examples:

- `backend/app/main.py` → `require_admin_key()`
- `backend/tests/test_security.py`
- `backend/tests/test_bookings.py`

### 2. FastAPI `TestClient`

`TestClient(app)` sends requests directly into the ASGI app without starting
Uvicorn or opening a network port. It exercises routing, validation, auth,
status codes, and response bodies.

Repository examples:

- `backend/tests/test_redteam.py`
- `backend/tests/test_phase7_8.py`

### 3. Pytest fixtures and `monkeypatch`

Fixtures create isolated state (temporary files, `TestClient`). `monkeypatch`
temporarily replaces environment variables, module globals, or functions.

Useful patterns from this repo:

```python
monkeypatch.setattr(board, "BOARD_STATE_FILE", tmp_path / "board_state.json")
monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key")
monkeypatch.setattr(limiter, "max_requests", 1000)
```

### 4. GitHub Actions and secret scanning

CI creates a fresh machine on each push. It installs dependencies, runs the
secret scanner, runs backend tests, and builds the frontend.

Repository examples:

- `.github/workflows/ci.yml`
- `backend/tests/test_secrets.py`

### 5. CORS

A browser at one origin cannot read a response from another origin unless the
server allows it. Production must use an explicit allowlist; do not use `*`
together with credentials.

Repository example:

- `backend/app/main.py` → `allowed_origins()`

## Official reading (verified 2026-11-07)

- [Python `secrets.compare_digest`](https://docs.python.org/3/library/secrets.html#secrets.compare_digest)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [FastAPI testing tutorial](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest monkeypatch guide](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
- [GitHub Actions quickstart](https://docs.github.com/en/actions/writing-workflows/quickstart)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

## Practice checklist

- [ ] Explain why `==` is risky for secret comparison.
- [ ] Open `require_admin_key()` and trace the 503, 401, and success paths.
- [ ] Run `cd backend && python -m pytest -q`.
- [ ] Add one new assertion to a `TestClient` test.
- [ ] Explain what a `monkeypatch` actually restores after the test.
- [ ] Run `cd web && npm test -- --run` and `npm run build`.
- [ ] Read `.github/workflows/ci.yml` and list every job.

## 10-minute drill

1. Break `compare_digest` by replacing it with `==` temporarily.
2. Run the relevant tests.
3. Revert the change.
4. Write down why the tests might still pass even though the implementation is
   weaker — and why that means timing-safe code needs explicit review, not only
   functional tests.
