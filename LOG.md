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

## Day 9: Recruiter JD Interrogator
- 9A: Added `POST /api/recruiter/interrogate` with `<untrusted_jd>` prompt-injection delimiters (OWASP LLM01) and a 6,000-character input cap.
- 9B: Added `Interrogate.vue` with a sci-fi UI panel, sample JD & injection test payloads, and live SSE streaming using `useStream.js`.

## Day 10: Excuse Buster & In-Memory TTL Cache
- 10A: Implemented `backend/app/excuses.py` with 4 preset excuses and a thread-safe TTL cache (1 hour).
- 10A: Cache is strictly keyed by `(excuse_id, resume_mtime)` to ensure responses are grounded in current resume facts; added safeguard to only cache completed LLM streams.
- 10A: Added `GET /api/excuses` and `POST /api/excuse-buster` (streaming) to `main.py`.
- 10B: Created `web/src/components/ExcuseBuster.vue` (UI), integrated it into `App.vue`, added proper `Content-Type` headers, accessibility labels, and styled it to match the portfolio theme.

## Day 11: Case Studies (RAG Setup)
- 11A: Created `backend/app/projects_data.json` with structured, grounded case studies (Find Wachira a Job, AyuTech).
- 11A: Created `backend/app/projects.py` helper to load projects and generate deterministic SHA-256 hashes for `problem`, `build`, and `outcome` text chunks.
- 11A: Added `GET /api/projects` endpoint in `main.py` to expose project data.
- 11B: Created `web/src/components/Projects.vue` with a responsive grid of sci-fi case study panels.
- 11B: Added "Ask Monkey About This Build" functionality per card using a new streaming endpoint (`/api/projects/{project_id}/inspect`) that grounds the LLM in real project data (fixing hallucinations).
- 11B: Integrated `<Projects />` into `App.vue` and added a live stream display in the UI.
- 11B: Cleaned up UI components by standardizing on CSS theme variables and consolidated API URL logic.

## Day 12: Vector Embeddings & Retrieval (RAG)

### 12A: Deterministic Chunk Embeddings & Cosine Search
- Added `backend/app/embeddings.py` to embed every `iter_project_chunks()` chunk with Gemini `gemini-embedding-001` over `httpx`, requesting 768 dimensions with `outputDimensionality` (the model's native size is 3072).
- `text-embedding-004` is retired and returns HTTP 404, so `gemini-embedding-001` is now the default; `GEMINI_EMBEDDING_MODEL` can override it, with `gemini-embedding-2` as the fallback model.
- Added a SHA-256-keyed JSON cache (`backend/app/embeddings_cache.json`); `sync_embeddings()` only embeds uncached or incomplete chunks and prunes hashes for edited/deleted project chunks.
- Cache records preserve `sha256`, `project_slug`, `project_title`, `section`, `text`, and `vector` for future RAG citations.
- Added `search_similar_chunks(query, top_k=4)`, which embeds the query and ranks cached chunks with exact pure-Python cosine similarity.

### 12B: Optional pgvector Dual-Mode Search
- Added `backend/sql/init_pgvector.sql` with `CREATE EXTENSION vector`, the `project_chunks` table (`embedding vector(768)`), and an HNSW cosine index.
- When `DATABASE_URL` is set and `psycopg` is installed, `sync_embeddings()` upserts chunks into `project_chunks` and prunes stale rows; `search_similar_chunks()` uses pgvector `1 - (embedding <=> query_vec)` for cosine ranking.
- PostgreSQL mode is opt-in: install with `pip install "psycopg[binary]"` and run `backend/sql/init_pgvector.sql` once; no new required dependency was added.
- The local JSON cosine search remains the zero-config default and automatic fallback when PostgreSQL is unset, unreachable, missing `psycopg`, or not yet synced.
- Fixed Day 11 leftovers: removed stray `//` notes from the `Interrogate.vue` template and deleted a duplicate `/api/projects` route/import from `main.py`.
