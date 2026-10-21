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
