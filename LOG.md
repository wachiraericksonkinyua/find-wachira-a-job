# Build Log - Find Wachira a Job

## Day 1: Repo & Backend Skeleton
- Set up monorepo structure (`/backend` and `/web`).
- Configured `.gitignore` and isolated `.env` so secrets never touch Git.
- Built FastAPI `/health` endpoint with CORS middleware and verified interactive `/docs`.

## Day 5: Pet State API & Pinia Integration
- Added `/api/pet/state` and `/api/pet/interact` with file-backed pet state, relief points, and per-IP rate limiting.
- Added a Pinia pet store (`web/src/stores/pet.js`) with `fetchState()` and `interact()`, exposing reactive desperation, label, mood, quip, loading, and error.
- Connected `Pet.vue` to the store: live state on mount, note inputs for link/lead/intro/know_person, one-click book action, and server validation/rate-limit errors shown in the speech bubble.

## Day 6: Deployment Prep & Contact Links
- Made the API base URL configurable with `VITE_API_URL`, falling back to local FastAPI, and applied it to both the pet store and the health check.
- Added cut-corner GitHub, LinkedIn, email, and resume links below the bio with hover states and focus-visible accessibility rings.
- Verified the production build succeeds via `npm run build`.

## Day 6: Deterministic Resume Pipeline
- Added `backend/app/resume_data.json` as the single structured source of truth for contact details, skills, experience, projects, and education.
- Added `backend/app/resume.py`, which renders that JSON to a PDF with fpdf2 and caches the bytes until the data file's mtime changes.
- Exposed `GET /api/resume` (downloadable PDF) and `GET /api/resume.json` (the structured source, ready for future per-job AI tailoring).
- Wired the site's resume and email links to the API and the real address; added fpdf2 and its runtime dependencies to `requirements.txt`.

## Day 7: LLM Client
- Added `backend/app/llm.py`, a provider-agnostic client for Groq (OpenAI-compatible) and Gemini with a hard timeout, ordered fallback, and safe error messages.
- Delimited visitor text inside a `<context>` block and instructed the model to treat it as untrusted data, the first defense against prompt injection (OWASP LLM01).
- Exposed `GET /api/llm/status` (which providers have keys) and `GET /api/pet/judgment` (non-streaming monkey commentary; Day 8 upgrades it to SSE).
- Added a tighter per-IP rate limit for LLM routes, documented the env vars in `backend/.env.example`, and added httpx to `requirements.txt`.

## Day 8: SSE Streaming Judgment Box
- Added `stream_judgment()` in `backend/app/llm.py`: an async generator that reads Groq and Gemini token streams over `httpx`, wraps each token in a JSON-encoded SSE frame, falls back to the next provider, and always ends with `data: [DONE]`.
- Upgraded `GET /api/pet/judgment` to a `StreamingResponse` with `text/event-stream`, `Cache-Control: no-cache`, and `X-Accel-Buffering: no`, keeping the per-IP rate limit.
- Added `web/src/composables/useStream.js`, which reads the response with `fetch`, `ReadableStream`, and `TextDecoder`, exposes reactive `text`/`streaming`/`error` state, and cancels stale requests with `AbortController`.
- Wired a "Judge my scroll" trigger into `Pet.vue` so tokens stream live into the monkey's speech bubble, with a stop control.
- Loaded `backend/.env` automatically via `python-dotenv` so provider keys are available without manually exporting the file first.
