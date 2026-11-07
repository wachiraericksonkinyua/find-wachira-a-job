# Find Wachira a Job

A recruiter-facing portfolio that does more than list skills. It streams AI
commentary, scores job descriptions against real project evidence, renders a
deterministic PDF resume, and turns the job hunt into a live "desperation"
meter. Built with **FastAPI**, **Vue 3**, **pgvector**, and an ordered
**Groq → Gemini** LLM fallback.

> The LLM is never trusted with facts it did not receive. Every claim about
> Wachira is grounded in resume/project data, and every feature has a
> deterministic fallback that works without an API key.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Vue 3 + Vite + Pinia + Tailwind (Vercel)                        │
│  Cinematic 2.5D hero · Pet · Projects · Match · Interrogate      │
│  ExcuseBuster · RedTeamLab · Book                                │
└───────────────────────────────┬──────────────────────────────────┘
                                │ fetch + Server-Sent Events
┌───────────────────────────────▼──────────────────────────────────┐
│  FastAPI (Render)                                                │
│                                                                  │
│  /api/resume          deterministic fpdf2 PDF                    │
│  /api/match           embed → retrieve → synthesize → validate   │
│  /api/*/inspect|judgment|interrogate|excuse-buster   SSE streams │
│  /api/pet/*           atomic JSON state + sliding-window limits  │
│  /api/book            bookings + pet relief                      │
│  /api/admin/leads     constant-time admin key                    │
│  /api/redteam/*       4-level isolated prompt-injection CTF      │
│  /api/security/report live attack telemetry + OWASP coverage     │
└───────────────┬──────────────────────────────┬───────────────────┘
                │                              │
      ┌─────────▼─────────┐          ┌─────────▼──────────────┐
      │ Supabase Postgres │          │ Groq (primary)         │
      │ + pgvector        │          │ Gemini (fallback)      │
      │ (optional)        │          │ 20s timeout            │
      └───────────────────┘          └────────────────────────┘
```

The backend runs with zero infrastructure: without Postgres it uses a local
embedding cache and JSON files; without LLM keys it returns grounded,
deterministic fallbacks.

---

## Key Features

### Deterministic PDF resume
`GET /api/resume` renders `resume_data.json` with **fpdf2** into a PDF cached by
the data file's mtime. The public download is generated from structured data,
so it cannot invent experience the way a live LLM call could.
`GET /api/resume.json` exposes the same source for future per-job tailoring.

### RAG Match Engine
`POST /api/match` takes a job description, embeds it, retrieves the top four
project chunks (pgvector cosine search, or local JSON cosine fallback), and asks
the LLM for strict JSON: `score`, `verdict`, `matched_skills`, `gaps`.
Every citation is attached **server-side** from retrieval metadata — the model
cannot fabricate its own sources. If parsing or the provider fails, a
deterministic score is computed as
`0.65 × best similarity + 0.35 × skill coverage`, so the endpoint always answers.

### SSE streaming
Four endpoints stream tokens as JSON-encoded Server-Sent Events and always end
with `data: [DONE]`:

- `GET /api/pet/judgment` — the mascot comments on recruiter behavior
- `GET /api/projects/{id}/inspect` — grounded project commentary
- `POST /api/recruiter/interrogate` — a verdict on a pasted JD
- `POST /api/excuse-buster` — a fact-based debunk of recruiter excuses

The frontend consumes them with `fetch` + `ReadableStream` (not `EventSource`,
which cannot send POST bodies) and cancels stale requests via `AbortController`.

### Pet desperation state model
`GET /api/pet/state` computes a 0–100 meter from time since last help, days
without an interview, rejection count, and relief earned today:

```
desperation = clamp(10 + min(40, neglect) + min(30, dry_spell)
                    + min(20, rejections × 2) - relief_today, 0, 100)
```

Interactions (`link`, `lead`, `intro`, `know_person`, `book`) award relief
points. State writes are lock-protected and atomic (`.tmp` + `replace`), and
the interaction log is capped at 50 entries. Notes for `intro`/`know_person`
reject third-party email addresses.

### Interview bookings & admin leads
`POST /api/book` validates and persists an interview request (Postgres when
configured, local JSON otherwise) and gives the pet 20 relief points.
`GET /api/admin/leads` returns bookings and pet leads only when
`X-Admin-Key` matches `ADMIN_API_KEY` using `secrets.compare_digest`.

### Graceful degradation
| Dependency | Missing → behavior |
| --- | --- |
| Groq key | Gemini is tried next |
| Both LLM keys | Deterministic grounded response |
| Postgres / pgvector | Local JSON embedding cache + cosine search |
| Embedding provider | Keyword-overlap citations |

---

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/telemetry` | Vector store, chunk count, providers, controls |
| `GET` | `/api/resume` | Deterministic PDF download |
| `GET` | `/api/resume.json` | Structured resume source |
| `GET` | `/api/projects` | Case studies |
| `GET` | `/api/projects/{id}/inspect` | SSE project commentary |
| `GET` | `/api/pet/state` | Computed desperation state |
| `POST` | `/api/pet/interact` | Record relief interaction |
| `GET` | `/api/pet/judgment` | SSE mascot commentary |
| `POST` | `/api/recruiter/interrogate` | SSE JD verdict |
| `POST` | `/api/match` | RAG match score + citations |
| `GET` | `/api/excuses` | Preset recruiter excuses |
| `POST` | `/api/excuse-buster` | SSE grounded debunk |
| `POST` | `/api/book` | Interview booking |
| `GET` | `/api/admin/leads` | Protected leads (admin key) |
| `GET` | `/api/llm/status` | Which providers are configured |
| `GET` | `/api/redteam/levels` | Four CTF levels and defenses (never flags) |
| `POST` | `/api/redteam/attack/{level}` | Rate-limited, isolated attack simulation |
| `POST` | `/api/redteam/submit` | Timing-safe flag verification + leaderboard |
| `GET` | `/api/redteam/leaderboard` | Nicknames-only scores |
| `GET` | `/api/security/report` | Attack attempts, blocks, solves, OWASP coverage |

Interactive docs: `http://127.0.0.1:8000/docs`

---

## Security

See [THREAT_MODEL.md](THREAT_MODEL.md) for the full OWASP LLM Top 10 mapping.

| Control | Implementation |
| --- | --- |
| Prompt injection (LLM01) | Untrusted input wrapped in `<untrusted_*>` delimiters; model told to treat it as data |
| Grounded citations | Retrieval metadata attached server-side, never model-generated |
| Abuse / cost limits (LLM10) | Sliding-window limiter, 5 requests / 60 s / IP on LLM routes; 30 / 60 s in the CTF |
| Input bounds | JD ≤ 6,000 chars, notes ≤ 280, role/company ≤ 120, attacks ≤ 1,000 |
| Admin auth | `secrets.compare_digest` against `ADMIN_API_KEY` |
| Red-team sandbox | Four isolated fake-flag levels, hashed-IP attempt logs, nickname sanitization, timing-safe flag checks |
| Secret hygiene | Keys stay server-side; telemetry returns provider names only |
| CORS | Explicit local origins + `ALLOWED_ORIGINS` allowlist, never `*` |
| PII guard | Third-party emails rejected in intro/know_person notes |
| Output handling | Strict JSON validation; Vue escapes all rendered text |

---

## Quickstart

### Backend

```bash
git clone https://github.com/<you>/find-wachira-a-job.git
cd find-wachira-a-job

cp backend/.env.example backend/.env   # add at least one provider key

python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt

cd backend
uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000` · Docs: `http://127.0.0.1:8000/docs`

Optional Postgres/pgvector: run `backend/sql/init_pgvector.sql` against your
database and set `DATABASE_URL` / `DIRECT_URL`.

### Frontend

```bash
cd web
npm ci
npm run dev
```

Vite runs at `http://127.0.0.1:5173` and defaults to the local API. Override with
`VITE_API_URL` for a deployed backend.

### Tests

```bash
cd backend && pytest -q          # 27 backend tests (includes secret scan)
cd web && npm test               # 79 Vitest tests
cd web && npm run build          # production build
```

---

## Deployment

### Backend → Render

`render.yaml` is a ready Blueprint:

- `rootDir: backend`
- `buildCommand: pip install -r requirements.txt`
- `startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- health check at `/health`

Set the `sync: false` secrets in the Render dashboard:
`GROQ_API_KEY`, `GEMINI_API_KEY`, `ADMIN_API_KEY`, and
`ALLOWED_ORIGINS=https://<your-app>.vercel.app`.
`DATABASE_URL` / `DIRECT_URL` are optional.

### Frontend → Vercel

Import the repo, set **Root Directory** to `web`, and let Vercel detect Vite.
`web/vercel.json` adds SPA rewrites so client-side routes resolve to
`index.html`. Set `VITE_API_URL` to the Render service URL.

### CI

`.github/workflows/ci.yml` runs on every push/PR to `main`:

- **secret-scan** — checks that `.env`, `bookings.json`, and `pet_state.json`
  stay untracked/gitignored and scans tracked files for `gsk_`, `AIza`, and
  credentialed Postgres URL patterns
- **backend** — Python 3.12, installs `requirements.txt` + `pytest`, runs `pytest -q`
- **frontend** — Node 20, `npm ci` and `npm run build`

`.github/workflows/keepalive.yml` pings `secrets.BACKEND_HEALTH_URL` daily at
08:00 UTC (and on manual dispatch) to keep the Render service and Supabase
project awake. Point it at `/api/telemetry` to also warm the database
connection. The job skips cleanly when the secret is unset.

---

## Project Structure

```
.
├── .github/workflows/ci.yml      CI: secret scan + backend tests + frontend build
├── .github/workflows/keepalive.yml  Daily Render/Supabase health ping
├── render.yaml                   Render Blueprint (FastAPI)
├── promptfooconfig.yaml          Automated red-team eval for the CTF levels
├── LEARNING_RESOURCES.md         Saved Days 16–44 study library
├── THREAT_MODEL.md               OWASP LLM Top 10 mapping
├── backend/
│   ├── app/
│   │   ├── main.py               Routes, CORS, auth, rate limits
│   │   ├── llm.py                Groq/Gemini clients, prompts, SSE
│   │   ├── match.py              RAG match engine + deterministic fallback
│   │   ├── embeddings.py         Chunking, embeddings, pgvector/local search
│   │   ├── pet.py                Desperation state model
│   │   ├── bookings.py           Bookings + admin leads
│   │   ├── redteam.py            4-level CTF, logs, leaderboard, report
│   │   ├── excuses.py            Presets + TTL cache
│   │   ├── resume.py             Deterministic fpdf2 renderer
│   │   └── rate_limit.py         Sliding-window limiter
│   ├── sql/init_pgvector.sql     pgvector, bookings, pet_leads schema
│   └── tests/                    pytest suite
└── web/
    ├── vercel.json               SPA rewrites
    ├── src/                      Vue components, Pinia store, composables
    └── tests/                    Vitest + Vue Test Utils suite
```
