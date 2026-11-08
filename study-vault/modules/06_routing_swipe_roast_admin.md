# Module 06 — Multi-Page Routing, Swipe Decks, Roast Wall, and Owner Admin

**Days covered:** Day 47

## The one-sentence version

Split a single-page portfolio into real routes, make the project deck feel like a
Tinder card stack, keep anonymous feedback behind a moderation queue, and give
the owner an admin surface that edits the live resume and regenerates the PDF.

---

## 1. Multi-page routing with Vue Router

### What changed

- The canonical router is `web/src/router/index.js`.
- `web/src/router.js` is a compatibility re-export, so older imports still work.
- Routes map one page to one responsibility:

| Path | Page | Responsibility |
| --- | --- | --- |
| `/` | `HomePage.vue` | 2.5D desk intro and 10-second pitch |
| `/projects` | `ProjectsPage.vue` | Swipe deck + grid toggle |
| `/wall` | `WallPage.vue` | Anonymous Roast Wall |
| `/match` | `MatchPage.vue` | RAG match + interrogator |
| `/lab` | `LabPage.vue` | 4-level prompt-injection CTF |
| `/board` | `BoardPage.vue` | Talent board + apply assistant |
| `/admin` | `AdminDashboard.vue` | Owner-only dashboard |

### Key ideas

- **History mode:** `createWebHistory()` gives clean URLs. Server hosting must
  rewrite unknown paths to `index.html` (Vercel already does this via
  `web/vercel.json`).
- **Route-level code splitting** is the next optimisation: lazy-import heavy
  pages with `() => import('../pages/LabPage.vue')`.
- **`scrollBehavior`** returns the saved position or the top of the page, which
  makes navigation feel like a real multi-page site.
- **Active links:** `RouterLink` + `active-class="nav-link-active"` gives the top
  navigation its current-page state without manual route watching.

```js
// web/src/router/index.js
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/projects', name: 'projects', component: ProjectsPage },
    { path: '/wall', name: 'wall', component: WallPage },
    { path: '/admin', name: 'admin', component: AdminDashboard },
  ],
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition || { top: 0 }
  },
})
```

**Repository examples:** `web/src/router/index.js`, `web/src/App.vue`,
`web/vercel.json`.

---

## 2. Tinder-style swipe deck

### Interaction model

`web/src/components/Projects.vue` keeps an index into the project list, so the
deck is just an array cursor:

```js
const deckIndex = ref(0)
const currentProject = computed(() => projects.value[deckIndex.value] || null)

function nextProject() {
  deckIndex.value = (deckIndex.value + 1) % projects.value.length
}
```

### Three actions, three behaviours

1. **Swipe right / ♥ Heart**
   - `POST /api/projects/{id}/react` with `{ "reaction": "heart" }`.
   - The server returns the new counts.
   - The deck advances only when the request succeeds.
2. **Swipe left / 🔥 Roast It**
   - Opens an inline textarea on the card.
   - Submits to `/api/roast-wall` with the current category as the target tag.
   - The roast is `pending`, then the deck advances after a short Ugali comeback.
3. **Click card body**
   - Opens the detail modal with Problem, Build, Outcome, stack, live URL, and
     GitHub URL.

### Touch and keyboard

- Touch handlers compare `changedTouches[0].clientX` on start/end and ignore
  movements below 45 px, so vertical scrolling still works.
- Arrow-key handlers support desktop users.
- Buttons live inside the card, so every action uses `@click.stop` to avoid also
  opening the modal.

```js
function onTouchEnd(event) {
  const endX = event.changedTouches?.[0]?.clientX ?? touchStartX
  const delta = endX - touchStartX
  if (Math.abs(delta) < 45) return
  delta < 0 ? nextProject() : previousProject()
}
```

### Testability

The deck exposes stable text (`SWIPE MODE`, `GRID MODE`, `HEART`, `ROAST IT`) so
Vitest can drive it without knowing internal component structure.

**Repository examples:** `web/src/components/Projects.vue`,
`web/tests/components/SwipeDeck.test.js`.

---

## 3. Anonymous Roast Wall and moderation state machine

### State machine

```text
POST /api/roast-wall
        │
        ▼
   status = pending
        │
   ┌────┴─────┐
   ▼          ▼
approved   rejected
   │
   ▼
GET /api/roast-wall  (public sees only approved)
```

- `POST /api/roast-wall` stores `text`, optional `advice`, optional `target`,
  and `status="pending"`.
- `GET /api/roast-wall` filters `status="approved"` and adds
  `author: "@anonymous_dev"`.
- Admin `GET /api/admin/moderation` returns only pending roasts and pending
  board entries.
- Approve uses `POST /api/admin/roast/{id}/approve`; delete uses
  `DELETE /api/admin/roast/{id}`.

### Privacy rules

- Never accept or store an email, IP address, or company name on the public roast
  form.
- Strip control characters and HTML tags before validation.
- Return only `id`, `author`, `target`, `text`, `advice`, and `created_at` in the
  public response.
- A target tag is a topic (`Portfolio UI`, `Printer Whisperer`), not a person.

### Seeding safely

Three approved demo roasts are seeded **only when the store is completely empty**.
A real pending or rejected submission therefore never gets hidden behind demo
content — which also keeps the moderation tests deterministic.

```python
def _ensure_seed_roasts() -> None:
    with _lock:
        roasts = _load_json_list(ROASTS_FILE, "roasts")
        if roasts:
            return
        _save_json_list(ROASTS_FILE, "roasts", _seed_roasts())
```

**Repository examples:** `backend/app/roasts.py`,
`backend/app/content_store.py`, `web/src/components/RoastWall.vue`,
`web/tests/components/RoastWall.test.js`.

---

## 4. Owner admin authentication and lead aggregation

### Timing-safe admin key

```python
def require_admin_key(x_admin_key: str | None) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin key is not configured.")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin key.")
```

Why `compare_digest`? A normal `==` can short-circuit on the first wrong byte.
`compare_digest` takes the same time for equal-length inputs, so response timing
does not leak how much of the key was correct. Missing configuration returns
`503`, not `401`, so a deploy mistake is visible instead of silently locking the
owner out.

The dashboard stores the key in `sessionStorage` only — it disappears when the
tab closes and is never written to `localStorage`.

### Unified lead feed

`GET /api/admin/leads` returns:

```json
{
  "bookings": [],
  "pet_leads": [],
  "leads": [
    { "kind": "booking", "name": "…", "company": "…", "notes": "…" },
    { "kind": "link", "notes": "https://…" },
    { "kind": "know_person", "notes": "…" }
  ]
}
```

The unified `leads` array is what the dashboard table renders. The raw
`bookings` and `pet_leads` arrays stay available for older clients.

**Repository examples:** `backend/app/main.py`, `backend/app/bookings.py`,
`backend/app/pet.py`, `web/src/pages/AdminDashboard.vue`.

---

## 5. Live resume editing and PDF regeneration

### Persistence design

- `resume_data.json` is the immutable seed.
- `resume_override.json` stores owner edits.
- `load_resume_data()` merges the seed, the override, and custom projects where
  `include_in_resume=True`.
- `save_resume_data()` writes the override atomically and clears the PDF cache.

```python
def save_resume_data(payload: ResumeAdminUpdate) -> dict:
    override = _read_json(OVERRIDE_FILE)
    for key, value in payload.model_dump(exclude_none=True).items():
        if key in _EDITABLE_KEYS:
            override[key] = value
    _write_json_atomic(OVERRIDE_FILE, override)
    global _cache
    with _lock:
        _cache = None
    return load_resume_data()
```

### Cache invalidation

`render_resume_pdf()` keys its cache on:

1. `resume_data.json` modification time
2. `resume_override.json` modification time
3. `content_store.project_revision()`

So any resume edit, project add, project update, or project delete produces a
fresh PDF on the next `GET /api/resume`.

### Why the PDF is deterministic

The public download never calls an LLM. It renders structured, owner-approved
data with `fpdf2`. That prevents the resume from inventing experience and makes
the output reproducible in tests.

### Test-friendly PDFs

`pdf.set_compression(False)` keeps text streams searchable, so a test can assert:

```python
pdf = client.get("/api/resume")
assert pdf.content.startswith(b"%PDF")
assert b"Resume Include Test Project" in pdf.content
```

**Repository examples:** `backend/app/resume.py`, `backend/app/portfolio.py`,
`backend/tests/test_admin_wall_swipe.py`.

---

## 6. Schema evolution without a migration framework

This project uses `CREATE TABLE IF NOT EXISTS` plus idempotent `ALTER TABLE`
statements:

```sql
ALTER TABLE roast_wall ADD COLUMN IF NOT EXISTS target TEXT;
ALTER TABLE portfolio_projects ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'Engineering';
ALTER TABLE portfolio_projects ADD COLUMN IF NOT EXISTS include_in_resume BOOLEAN NOT NULL DEFAULT TRUE;
```

Why this is acceptable here:

- The schema is small and additive.
- `ADD COLUMN IF NOT EXISTS` is safe to run on every process start.
- The JSON fallback stores the same field names, so tests cover both shapes.

When the project grows, switch to Alembic (or another migration tool) so column
renames, backfills, and index changes are versioned and reversible.

**Repository examples:** `backend/app/content_store.py`,
`backend/sql/init_pgvector.sql`.

---

## 7. Testing strategy

### Backend: prove the state machine

`backend/tests/test_admin_wall_swipe.py` covers:

- submitting a roast → hidden from the public wall
- admin approval → visible with `@anonymous_dev` and the target tag
- adding a project with `include_in_resume=True` → valid `%PDF` containing the title
- adding a project with `include_in_resume=False` → absent from the PDF
- `PUT /api/admin/resume` → edited summary appears in the PDF
- every `/api/admin/*` route → `401` without a valid `X-Admin-Key`
- `/api/projects/{id}/react` alias → heart count persists

### Frontend: drive the real component

`web/tests/components/SwipeDeck.test.js` mounts the deck and verifies:

- first card and progress counter
- grid toggle
- heart POST + deck advance
- quick roast POST + Ugali comeback
- detail modal content

`web/tests/components/RoastWall.test.js` verifies:

- anonymous author and target tags render
- preset target options exist
- submission posts the selected target
- custom target text is sent

### Test isolation rules

- Monkeypatch every JSON file path to `tmp_path`.
- Monkeypatch `resume.OVERRIDE_FILE` too.
- Clear `resume._cache`.
- Set `DATABASE_URL=""` so tests never touch live Postgres.
- Raise rate limits for the duration of the test.

**Repository examples:** `backend/tests/conftest.py`,
`backend/tests/test_admin_wall_swipe.py`, `web/tests/setup.js`.

---

## 8. Official reading and tutorials (verified 2026-11-08)

### Vue and routing

- [Vue Router guide](https://router.vuejs.org/guide/)
- [Vue Router: programmatic navigation](https://router.vuejs.org/guide/essentials/navigation.html)
- [Vue Router: dynamic route matching](https://router.vuejs.org/guide/essentials/dynamic-matching.html)
- [Vue: component basics](https://vuejs.org/guide/essentials/component-basics.html)
- [Vue: event handling](https://vuejs.org/guide/essentials/event-handling.html)
- [Vue: form input bindings](https://vuejs.org/guide/essentials/forms.html)
- [Vue: accessibility best practices](https://vuejs.org/guide/best-practices/accessibility.html)

### Testing

- [Vitest guide](https://vitest.dev/guide/)
- [Vue Test Utils guide](https://test-utils.vuejs.org/guide/)
- [FastAPI testing tutorial](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest monkeypatch guide](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)

### FastAPI, Pydantic, and security

- [FastAPI header parameters](https://fastapi.tiangolo.com/tutorial/header-params/)
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Python `secrets.compare_digest`](https://docs.python.org/3/library/secrets.html#secrets.compare_digest)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)

### PostgreSQL and persistence

- [PostgreSQL `ALTER TABLE`](https://www.postgresql.org/docs/current/sql-altertable.html)
- [PostgreSQL: altering a table](https://www.postgresql.org/docs/current/ddl-alter.html)
- [Python `tempfile`](https://docs.python.org/3/library/tempfile.html)
- [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace)

### PDF generation

- [fpdf2 documentation](https://py-pdf.github.io/fpdf2/)
- [fpdf2 tutorial](https://py-pdf.github.io/fpdf2/Tutorial.html)

### Touch and accessibility

- [MDN Touch events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)
- [WAI-ARIA modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [MDN ARIA `dialog` role](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/dialog_role)

---

## 9. Practice checklist

- [ ] Add a new route and a nav link without touching any page component twice.
- [ ] Keyboard-only: swipe the deck with arrow keys and open the modal with Enter.
- [ ] Turn on reduced motion and confirm the deck still works without animations.
- [ ] Submit a roast, confirm it is invisible publicly, approve it as admin, then
      confirm `@anonymous_dev` and the target tag appear.
- [ ] Submit `<script>alert(1)</script>` as a roast and verify it is stripped.
- [ ] Add a project with `include_in_resume=True` and confirm the text appears in
      the downloaded PDF.
- [ ] Add a project with `include_in_resume=False` and confirm it is absent.
- [ ] Edit the resume summary and confirm the PDF changes on the next download.
- [ ] Call every `/api/admin/*` route with no key and with a wrong key; confirm
      both return `401`.
- [ ] Explain why `secrets.compare_digest` is used instead of `==`.
- [ ] Run `pytest -q`, `npm test -- --run`, and `npm run build`.

## 10. 10-minute drill

Open `Projects.vue` and trace one ♥ click end to end:

1. Which button fires?
2. Which fetch URL and JSON body leave the browser?
3. Which FastAPI route receives it?
4. Which `content_store` function writes the reaction?
5. How does the returned count reach the card?
6. Why does the deck advance only after the request succeeds?

Then repeat the trace for a 🔥 roast and explain the difference between a project
reaction and a moderation-queue submission.
