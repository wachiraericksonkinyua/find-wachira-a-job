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
