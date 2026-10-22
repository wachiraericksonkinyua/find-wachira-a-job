# Architecture Guide: Find Wachira a Job

A senior-engineer walkthrough of Days 1-6, written for the person who built it.

You did not just make a website. You made a small distributed system: a browser app, a
Python API, two different persistence strategies, a rate limiter, and a build pipeline.
This guide connects the dots so you can explain every moving part in an interview.

Read it in order the first time. The analogies are there to give you a mental model; the
line references are there so you can jump back into the code and prove the details.

---

## Quick File Map

```text
find-wachira-a-job/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, routes, CORS
│   │   ├── pet.py             validation, state math, file persistence
│   │   ├── pet_state.json     live pet state (gitignored, machine-local)
│   │   ├── rate_limit.py      in-memory sliding-window limiter
│   │   ├── resume.py          deterministic PDF renderer + mtime cache
│   │   └── resume_data.json   resume source of truth
│   ├── requirements.txt
│   └── .env                   secrets/config (gitignored)
├── web/
│   ├── index.html             #app mount point + fonts
│   ├── vite.config.js         Vue + Tailwind plugins
│   └── src/
│       ├── main.js            createApp + createPinia + mount
│       ├── style.css          design tokens, grid, .panel clip-path
│       ├── App.vue            page shell, pitch, contact links, mode toggle
│       ├── stores/pet.js      Pinia store: state + API calls
│       ├── components/Pet.vue floating monkey, menu, mouse tracking
│       └── components/HelloWorld.vue  unused Vite scaffold (safe to delete)
└── LOG.md                     build log
```

---

## 1. High-Level Architecture & How Frontend + Backend Connect

### The restaurant analogy

Think of the app as a restaurant:

- **The dining room** is the browser. `App.vue` is the room layout, `Pet.vue` is the
  waiter who takes your order and reacts to you.
- **The order pad** is Pinia (`stores/pet.js`). Both the waiter and the kitchen trust the
  same pad; nobody shouts state across the room.
- **The kitchen** is FastAPI (`main.py`). It decides what is allowed and what gets cooked.
- **The bouncer at the kitchen door** is `rate_limit.py`. He checks how many orders you
  placed in the last minute before letting another one through.
- **The pantry** is persistence. `pet.py` owns `pet_state.json`; `resume.py` owns
  `resume_data.json`.
- **The address of the restaurant** is `VITE_API_URL`. In development it is
  `http://127.0.0.1:8000`; in production it is whatever you set in the build environment.
- **The border checkpoint** between browser and kitchen is CORS. The browser will not let
  JavaScript from one origin read a response from another origin unless the server says
  "yes, that origin is allowed."

### The flow, drawn

```text
 USER
  │ clicks "Share a link" (Pet.vue)
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ BROWSER (origin: http://localhost:5173)                              │
│                                                                      │
│  App.vue / Pet.vue                                                   │
│      │  storeToRefs() keeps UI reactive                              │
│      ▼                                                               │
│  Pinia store (web/src/stores/pet.js)                                 │
│      │  interact('link', note)                                       │
│      │  fetch(`${API_URL}/api/pet/interact`, { method: 'POST', ... })│
│      ▼                                                               │
│  Browser networking layer                                            │
│      │  VITE_API_URL = http://127.0.0.1:8000                         │
│      │  1. OPTIONS /api/pet/interact   <-- CORS preflight            │
│      │  2. POST /api/pet/interact      <-- only if preflight passes  │
└──────┼───────────────────────────────────────────────────────────────┘
       │  crosses origin boundary
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FASTAPI (backend/app/main.py)                                        │
│                                                                      │
│  CORSMiddleware                                                     │
│      │  checks Origin against allow_origins                          │
│      │  replies with Access-Control-Allow-* headers                  │
│      ▼                                                               │
│  Route: POST /api/pet/interact                                       │
│      │  payload: InteractRequest (Pydantic validates -> 422 on bad)  │
│      ▼                                                               │
│  rate_limit.py: interact_limiter.allow(client_ip)                    │
│      │  5 requests / 60 seconds / IP                                 │
│      │  too many? -> HTTP 429                                       │
│      ▼                                                               │
│  pet.py: record_interaction(type, note)                              │
│      │  acquire threading.Lock()                                     │
│      │  load pet_state.json                                          │
│      │  update relief, timestamps, interactions[]                    │
│      │  write pet_state.json.tmp -> replace pet_state.json           │
│      ▼                                                               │
│  JSON response { desperation, label, mood, quip, relief_gained, ... }│
└──────┼───────────────────────────────────────────────────────────────┘
       │  HTTP 200 + JSON
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ BROWSER                                                              │
│  pet.js applies response to refs (desperation, label, mood, quip)    │
│  Vue's reactivity system re-renders Pet.vue and its meter            │
│  UI shows the new percentage, sprite, and speech bubble              │
└──────────────────────────────────────────────────────────────────────┘
```

The resume path is the same shape, but read-only and without the bouncer:

```text
<a :href="`${API_URL}/api/resume`"> in App.vue
        │  browser navigation/download (not fetch)
        ▼
FastAPI GET /api/resume (main.py)
        ▼
resume.py render_resume_pdf()
        │  mtime cache hit? return cached bytes
        │  else read resume_data.json -> fpdf2 -> PDF bytes
        ▼
Response(media_type="application/pdf",
         Content-Disposition: attachment; filename="...")
```

### GET vs POST

| | `GET` | `POST` |
|---|---|---|
| Purpose | Read something | Change something |
| Body | Normally none | JSON body (`{ type, note }`) |
| Side effects | Must be none | Expected: writes state |
| Our examples | `/health`, `/api/resume`, `/api/resume.json`, `/api/pet/state` | `/api/pet/interact` |
| Validation | Query/path params | Pydantic request body; bad body -> `422` |
| Retry safety | Safe to retry | Not automatically safe; a retry may add points twice |
| CORS preflight | Usually not (simple request) | Yes, because `Content-Type: application/json` is not a CORS-simple header |

`GET /api/pet/state` reads the JSON file and computes the current meter. It does not write
anything. `POST /api/pet/interact` is the only route that mutates `pet_state.json`.

### What is that OPTIONS request in the logs?

When `fetch()` sends a cross-origin `POST` with `Content-Type: application/json`, the
browser first sends a "preflight" request:

```http
OPTIONS /api/pet/interact HTTP/1.1
Origin: http://localhost:5173
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type
```

This is the browser asking the server: "May a page from `localhost:5173` send a POST with
a JSON content type to you?" FastAPI's `CORSMiddleware` (`backend/app/main.py:10-21`)
answers with headers such as:

```http
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

If the origin is not in `allow_origins`, the browser blocks the real request. The server
might still log the OPTIONS or even return a response, but the browser refuses to expose
it to your JavaScript. This is why "it works in Postman but not the browser" is usually
CORS: Postman is not a browser and does not enforce the same-origin policy.

Important production note: the allow-list currently contains only `localhost`/`127.0.0.1`
on ports `5173` and `5174`. When you deploy, add the real frontend origin. Never solve
this by using `allow_origins=["*"]` together with `allow_credentials=True`; browsers
reject that combination, and it is sloppy security.

`GET /health` is a simple cross-origin GET, so the browser can usually send it without a
preflight. The resume link is a normal browser navigation/download, not a `fetch`, so CORS
does not gate it the same way; the server's `Content-Disposition` header makes the browser
download the file.

### Why `VITE_API_URL` matters

`web/src/stores/pet.js:4` and `web/src/App.vue:9` both do:

```js
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
```

Vite replaces `import.meta.env.VITE_API_URL` at build time. Only variables prefixed with
`VITE_` are exposed to client code. If the variable is missing, the fallback keeps local
development working. Set it when building for production:

```bash
VITE_API_URL=https://api.example.com npm run build
```

This is configuration, not a secret. Never put an API key in a `VITE_` variable; it ships
to the browser.

---

## 2. Backend Code Walkthrough

### `backend/app/main.py` - the front desk

**The app object (`main.py:8`)**

```python
app = FastAPI(title="Find Wachira a Job API", version="0.1.0")
```

This object owns the route table, middleware, validation hooks, and the automatic
OpenAPI docs at `/docs`. Uvicorn imports it with `uvicorn app.main:app`.

**CORS middleware (`main.py:10-21`)**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[...],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Analogy: the middleware is the border checkpoint. It inspects the `Origin` header and
decides whether the browser is allowed to read the response. `allow_credentials=True`
means cookies/auth headers could be sent, which is exactly why the origin list must be
explicit.

**`Request` vs `Response` (`main.py:1,57,33-39`)**

- `Request` is the incoming HTTP envelope. We use it at `main.py:60` to get
  `request.client.host`, the caller's IP, for rate limiting.
- `Response` is the outgoing envelope. Most routes return a Python `dict` and FastAPI
  serializes it to JSON automatically. `/api/resume` needs raw bytes, so at
  `main.py:33-39` we return a `Response` with `media_type="application/pdf"` and a
  `Content-Disposition` header.

**`async def` vs `def` (`main.py:24` vs `main.py:29,43,50,57`)**

`health_check` is `async def` because it only does a tiny amount of in-memory work and
never blocks. The other routes are plain `def` on purpose:

- `pet_state`, `pet_interact`, `resume_pdf`, and `resume_json` do blocking work: reading
  and writing files, acquiring locks, and rendering a PDF with fpdf2.
- FastAPI runs sync routes in a worker threadpool, so a slow file write or PDF render
  does not freeze the event loop that serves everyone else.
- If you made these `async def`, you would have to use async file I/O or push the blocking
  work to a thread manually; otherwise one slow request would stall the server.

Rule of thumb: `async def` when you await non-blocking I/O; `def` when the work is
CPU-bound or uses blocking libraries like `fpdf2`.

**The endpoints**

| Route | Method | What it does | Status codes |
|---|---|---|---|
| `/health` | GET | Liveness probe; returns `{"status": "ok", "db": true}` | `200` |
| `/api/resume` | GET | Renders/caches and returns the PDF | `200` |
| `/api/resume.json` | GET | Returns the structured resume source | `200` |
| `/api/pet/state` | GET | Loads state and computes the meter | `200` |
| `/api/pet/interact` | POST | Validates, rate-limits, mutates state, returns new state | `200`, `422`, `429` |

A note on `/health`: it reports `"db": true` even though there is no database. It is a
liveness signal, not a deep dependency check. In production you would add a real readiness
check (database ping, disk check) and keep the shallow liveness check separate.

`/api/resume.json` is deliberately separate from `/api/resume`. The JSON is the source of
truth; the PDF is a presentation of it. That separation is what makes future AI tailoring
safe: an LLM should edit structured data, not hand-write a PDF.

**Error flow**

- Pydantic validation failure -> FastAPI automatically returns `422` with `detail` as a
  list of error objects.
- Rate limit exceeded -> `main.py:62-66` raises `HTTPException(429, detail="...")`; the
  `detail` is a string.
- This difference is why the frontend has to handle both an array and a string at
  `web/src/stores/pet.js:57-60`.

### `backend/app/pet.py` - the brain and the filing cabinet

**Constants and configuration (`pet.py:13-39`)**

- `STATE_FILE` (`pet.py:13`) uses `Path(__file__).with_name("pet_state.json")`, so the
  state sits next to the Python file no matter what directory you launch from. This is
  more reliable than a relative `"pet_state.json"`.
- `_lock = threading.Lock()` (`pet.py:14`) is one shared lock for all state reads/writes.
- `RELIEF_POINTS` (`pet.py:17-23`) maps each action to how much desperation it removes.
- `PRIVATE_NOTE_TYPES` (`pet.py:27`) and `NOTE_REQUIRED_TYPES` (`pet.py:29`) encode
  business rules near the validation that enforces them.
- `EMAIL_RE` (`pet.py:31`) blocks third-party emails in intro/know-person notes.

**Pydantic validation (`pet.py:42-66`)**

```python
class InteractRequest(BaseModel):
    type: Literal["link", "lead", "intro", "know_person", "book"]
    note: str | None = Field(default=None, max_length=280)
```

- `BaseModel` is the contract. FastAPI reads the JSON body, constructs this model, and
  rejects the request with `422` if the shape is wrong.
- `Literal[...]` means `type` must be exactly one of those five strings. It is better than
  a free string plus an `if/else`, because invalid values are rejected before your code
  runs.
- `Field(max_length=280)` stops someone from posting a novel.
- `@field_validator("note")` (`pet.py:48-55`) normalizes input: trims whitespace and turns
  an empty string into `None`. Normalizing in one place means the rest of the code does not
  need to repeat `if note and note.strip()`.
- `@model_validator(mode="after")` (`pet.py:57-66`) sees the whole model, so it can enforce
  cross-field rules:
  - Some actions require a note.
  - Intro/know-person notes may not contain an email address.
- `EMAIL_RE` is a pragmatic guard, not a full RFC 5322 email parser. For this use case,
  "does it look like an email?" is enough. If you needed bulletproof validation, you would
  use a dedicated library and decide whether to allow quoted/local domains.

Analogy: Pydantic is the form at the bank counter. If you leave a required field blank or
write gibberish, the clerk hands it back before it reaches the vault.

**Locking and atomic writes (`pet.py:14,92-122`)**

```python
with _lock:
    state = _load_unlocked()
    ...
    _write_unlocked(state)
```

Two recruiters clicking at the same time could otherwise do:

1. Request A reads `relief_today = 5`.
2. Request B reads `relief_today = 5`.
3. A writes `5 + 5 = 10`.
4. B writes `5 + 8 = 13`, erasing A's update.

The lock makes load-mutate-save one indivisible operation. This is the same idea as a
database transaction, implemented for a JSON file.

The atomic write (`pet.py:92-96`) is:

```python
tmp = STATE_FILE.with_suffix(".tmp")
tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
tmp.replace(STATE_FILE)
```

Writing directly to `pet_state.json` risks a half-written file if the process crashes
mid-write. Writing to a temporary file and renaming is atomic on POSIX filesystems: readers
see either the old complete file or the new complete file, never a torn one. Analogy: you
write the new will on a fresh sheet, then swap it into the folder in one motion.

If the file is missing or corrupt (`pet.py:99-112`), `_load_unlocked` seeds or resets it
instead of crashing the API. That is graceful degradation for a demo. In a real system you
would log the corruption loudly and alert, because silent reset can hide data loss.

**Desperation-O-Meter formula (`pet.py:185-222`)**

```text
desperation = clamp(
    10
    + neglect       # 2 points per hour without help, capped at 40
    + dry_spell     # 1 point per day without an interview, capped at 30
    + rejections    # 2 points per rejection, capped at 20
    - relief_today, # points earned today
    0, 100
)
```

Walk through the pieces:

- `base = 10`: the monkey starts mildly worried.
- `neglect` (`pet.py:190-194`): `hours_without_help * 2`, capped at 40. The cap prevents
  one very old timestamp from pinning the meter forever.
- `dry_spell` (`pet.py:195`): one point per day since the last interview, capped at 30.
- `rejections` (`pet.py:196`): two points per rejection, capped at 20. The input is also
  clamped with `max(0, ...)` so negative data cannot reduce desperation.
- `relief_today` (`pet.py:198-200`): only counts if `relief_date` is today. Yesterday's
  relief does not help today.
- The final `max(0, min(100, ...))` clamps the result.

The label (`pet.py:163-170`) and mood (`pet.py:173-182`) are presentation mappings:

| Desperation | Label | Passive mood |
|---|---|---|
| `<= 25` | Smug | `sleeping` |
| `26-50` | Hungry | `smug` |
| `51-75` | Starving | `smug` |
| `> 75` | Crying in binary | `anxious` |

Yes, the naming is intentionally a little ironic: low desperation looks "smug", high
desperation looks "anxious". The backend owns this mapping so every client shows the same
thing.

**Recording an interaction (`pet.py:125-160`)**

Inside one lock, it:

1. Loads state.
2. Resets daily relief if the date changed (`pet.py:136-139`).
3. Adds `RELIEF_POINTS[action_type]` (`pet.py:141-142`).
4. Updates `last_help_at` (`pet.py:143`).
5. Appends an interaction log entry and trims the list to the last 50 (`pet.py:145-150`).
6. Writes atomically.
7. Returns the computed public state plus a happy mood and a quip.

Trimming the log is a memory/storage bound. Without it, the JSON grows forever and every
read gets slower and more expensive.

One subtle point: a `book` action updates `last_help_at` but not `last_interview_at`.
That means booking an interview relieves the meter today, but the dry-spell clock is not
reset. Is that the product behavior you want? If not, update `last_interview_at` for
`book`. This is a great example of a small business rule hiding in a timestamp field.

### `backend/app/rate_limit.py` - the bouncer

**The class (`rate_limit.py:6-20`)**

```python
class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
```

- `defaultdict(deque)` means "when I ask for a key that does not exist, create an empty
  double-ended queue for it." You do not need to check `if key not in self._hits`.
- Each client key (IP address) gets its own `deque` of request timestamps.
- `deque` gives O(1) `append` on the right and `popleft` on the left. That is exactly the
  queue behavior a sliding window needs.

**`allow()` (`rate_limit.py:22-38`)**

```python
now = time.monotonic()
cutoff = now - self.window_seconds
with self._lock:
    timestamps = self._hits[key]
    while timestamps and timestamps[0] <= cutoff:
        timestamps.popleft()
    if len(timestamps) >= self.max_requests:
        return False
    timestamps.append(now)
    self._maybe_sweep(cutoff)
    return True
```

Why `time.monotonic()` and not `time.time()`? Wall-clock time can jump backward or forward
when the system clock is adjusted (NTP, daylight saving, manual change). `monotonic()`
only moves forward, so a window cannot accidentally become huge or negative.

The algorithm in plain English:

1. Drop every timestamp older than `now - window`.
2. If the remaining count is at the limit, reject.
3. Otherwise record this request and allow it.

Analogy: a bouncer with a clipboard. He crosses out anyone who left more than a minute
ago, then checks how many names remain on the list. If the list is full, you wait.

**`_maybe_sweep()` (`rate_limit.py:40-46`)**

The dictionary of clients could grow forever if you see millions of unique IPs. The sweep
only runs when the dictionary reaches 1000 entries, then removes clients whose latest hit
is already outside the window. This is lazy cleanup: no background thread, no timer, just
amortized housekeeping when it matters.

**The shared limiter (`rate_limit.py:49-50`)**

```python
interact_limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
```

Five interactions per minute per IP, per process. That "per process" caveat matters: if
you run four Uvicorn workers, each worker has its own dictionary, so the effective limit
could become twenty. In production, move the counters to Redis (with an atomic
increment/expire or a sorted set) so all workers share one view. For a single-process demo,
this in-memory version is simple and correct.

Also note the proxy issue: behind Nginx or a cloud load balancer, `request.client.host` may
be the proxy's IP unless the proxy forwards the client address and Uvicorn is run with
`--proxy-headers` and a trusted `--forwarded-allow-ips` setting. Otherwise every user shares
one bucket.

### `backend/app/resume.py` and `resume_data.json` - the printing press

**The source of truth**

`resume_data.json` contains the facts. `resume.py` contains the layout. The renderer never
invents content; it only formats fields it is given. That is the whole safety argument.

**The renderer (`resume.py:61-144`)**

`_build_pdf()` creates an `FPDF` object (`resume.py:62-65`), then writes sections:

- Header: name, headline, contact line, links (`resume.py:67-93`).
- Summary (`resume.py:95-99`).
- Skills (`resume.py:101-108`).
- Experience (`resume.py:110-120`).
- Projects (`resume.py:122-131`).
- Education (`resume.py:133-142`).

Helpers keep the layout consistent:

- `_section()` (`resume.py:27-35`) prints a heading and a horizontal accent rule.
- `_bullet()` (`resume.py:38-48`) wraps long bullet text.
- `_entry_heading()` (`resume.py:51-58`) prints a bold title and an italic date/location
  line.

`multi_cell` wraps text; `cell` does not. Using `multi_cell` for summaries and bullets is
what prevents long lines from running off the page.

**The mtime cache (`resume.py:13-14,147-160`)**

```python
_cache: tuple[float, bytes] | None = None
_lock = threading.Lock()

def render_resume_pdf() -> bytes:
    mtime = DATA_FILE.stat().st_mtime
    with _lock:
        if _cache and _cache[0] == mtime:
            return _cache[1]
    pdf_bytes = _build_pdf(load_resume_data())
    with _lock:
        _cache = (mtime, pdf_bytes)
    return pdf_bytes
```

The cache key is the file's modification time, not the wall clock. If nobody edited
`resume_data.json`, `mtime` is unchanged, so every click returns the same bytes without
re-running fpdf2. As soon as you edit the JSON, `mtime` changes, the cache misses, and the
next request rebuilds the PDF.

Analogy: a photocopy on the counter. If the original document has not changed (same
"last modified" stamp), hand out the copy. When someone edits the original, shred the copy
and make a new one.

The lock protects the cache from two threads racing to write it. It is a small critical
section; the expensive PDF build happens outside the first lock, which keeps the lock hold
time short.

**How AI tailoring should fit later**

Do not let an LLM write the public PDF directly. Instead:

1. Read `resume_data.json` plus the job description.
2. Ask the LLM for a *structured* result (same JSON shape, reordered/rewritten bullets).
3. Validate that result with Pydantic against the same schema.
4. Render it with `_build_pdf()`.
5. Cache it per job description hash.

The public `/api/resume` stays deterministic. A separate `/api/resume/tailor` route can be
rate-limited, logged, and reviewed. You keep the engineering flex without letting a model
hallucinate a degree.

---

## 3. Frontend Code Walkthrough

### `web/src/main.js` - the ignition

```js
const app = createApp(App)
app.use(createPinia())
app.mount('#app')
```

- `createApp(App)` creates the Vue application rooted at `App.vue`.
- `app.use(createPinia())` installs Pinia before any component calls `usePetStore()`.
  Order matters: if a component tried to use a store before Pinia was installed, Vue would
  throw "getActivePinia() was called but there was no active Pinia."
- `app.mount('#app')` replaces the `<div id="app">` in `web/index.html:18` with the
  rendered app.

Analogy: `createApp` builds the house, `use(createPinia)` connects the electrical panel,
and `mount` plugs the house into the plot of land in `index.html`.

### `web/src/style.css` - the design language

**CSS custom properties (`style.css:2-11`)**

```css
:root {
  --bg: #0A0F1F;
  --card: #101A33;
  --ink: #E6F1FF;
  --mute: #8FA6C8;
  --line: #22345E;
  --ugali: #19E3FF;
  --leaf: #3DF5A6;
  --chili: #FF4D8D;
}
```

These are design tokens. Change `--ugali` once and every cyan accent in the app follows.
Analogy: a paint palette for the whole house, not a separate can of paint per room.

**Blueprint grid (`style.css:13-24`)**

```css
background-image:
  linear-gradient(var(--line) 1px, transparent 1px),
  linear-gradient(90deg, var(--line) 1px, transparent 1px);
background-size: 44px 44px;
background-attachment: fixed;
```

Two linear gradients draw horizontal and vertical lines. Repeating them every 44 pixels
creates graph paper. `background-attachment: fixed` keeps the grid still while content
scrolls, which sells the blueprint/sci-fi feel.

**The cut-corner panel (`style.css:27-38`)**

```css
.panel {
  background: var(--card);
  border: 1px solid var(--line);
  clip-path: polygon(
    0 0,
    calc(100% - 14px) 0,
    100% 14px,
    100% 100%,
    14px 100%,
    0 calc(100% - 14px)
  );
}
```

`clip-path` defines a visible polygon. The coordinates cut the top-right and bottom-left
corners at 14px. It is visual only: the element still occupies its full rectangular box
for layout and hit-testing. That is why the panels can sit in a normal flex row while
looking chamfered.

**Fonts (`style.css:40-42`, loaded in `index.html:14`)**

`font-orbitron`, `font-mono-tech`, and `font-pixel` are utility classes that map to the
Google Fonts imported in `index.html`. `Orbitron` carries the headings, `Share Tech Mono`
carries technical labels, and `Press Start 2P` carries the game-like microcopy.

### `web/src/stores/pet.js` - the shared order pad

**Pinia setup store (`pet.js:6-87`)**

```js
export const usePetStore = defineStore('pet', () => {
  const desperation = ref(0)
  ...
  return { desperation, label, mood, quip, loading, error, fetchState, interact }
})
```

This is the "setup store" syntax: the function body is like a component's `setup()`. You
create reactive state with `ref()`, define functions, and return what should be public.
Pinia unwraps the refs on the store instance, so in a component you write
`pet.desperation`, not `pet.desperation.value`.

Why `ref()` instead of `reactive()`? `ref()` works for primitives and objects, can be
reassigned, and plays nicely with destructuring via `storeToRefs()`. For a store with
independent scalar values, `ref()` is the simplest correct choice.

**`applyState()` (`pet.js:16-21`)**

This copies only known fields from the API response into the refs. It is a small boundary
layer: the server can add fields without breaking the UI, and the UI only trusts values it
knows how to display. The `typeof data.desperation === 'number'` check prevents a malformed
response from putting a string into a numeric meter.

**`fetchState()` (`pet.js:23-39`)**

```js
const res = await fetch(`${API_URL}/api/pet/state`)
if (!res.ok) throw new Error(...)
applyState(await res.json())
```

- `fetch` does not reject on HTTP 404/500; it resolves with `res.ok === false`. That is why
  the code checks `res.ok` explicitly.
- On success, `applyState` updates the refs and Vue re-renders every component using them.
- On failure, it sets a human-friendly `error` and logs the technical error.
- `finally` always clears `loading`, even if the request throws. This prevents a stuck
  spinner.

**`interact()` (`pet.js:41-75`)**

```js
body: JSON.stringify(note ? { type, note } : { type })
```

Only send `note` when there is one, so a "book" action stays a one-click request and does
not send `note: ""`.

The error handling is deliberately shape-aware:

```js
const data = await res.json().catch(() => ({}))
if (!res.ok) {
  const detail = data.detail
  error.value = Array.isArray(detail)
    ? detail[0]?.msg || 'That note did not pass validation.'
    : detail || `Something went wrong (HTTP ${res.status}).`
  return null
}
```

- `200`: `applyState(data)`, force `mood = 'happy'`, return the data.
- `422`: FastAPI/Pydantic sends `detail` as an array of validation errors, so take the
  first `msg`. Example: a `link` action with no note.
- `429`: our `HTTPException` sends `detail` as a string, so display it directly. Example:
  "Too many interactions! Let the monkey breathe a bit."
- Network failure: `fetch` rejects, the `catch` sets "The monkey could not reach the
  server."
- Always return `null` on failure so `Pet.vue` can leave the menu open and show the error.

**`import.meta.env.VITE_API_URL` (`pet.js:4`)**

Vite statically replaces this at build time. It is not a runtime lookup into `process.env`.
If you change `.env`, restart the dev server or rebuild. Only `VITE_`-prefixed variables
are included in the client bundle.

### `web/src/App.vue` - the page shell

**Local state (`App.vue:6-9`)**

```js
const apiOnline = ref(false)
const professionalMode = ref(false)
const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
```

`apiOnline` drives the green/red dot. `professionalMode` is a boolean passed down to the
pet. `API_URL` is the same configuration pattern as the store.

**Health check (`App.vue:12-22`)**

`onMounted` runs once after the component is mounted. It fetches `/health`, parses JSON,
and sets `apiOnline` based on `data.status === 'ok'`. If the backend is down, the `catch`
sets `false` and logs the error. This is a liveness indicator for the recruiter, not a
blocking gate: the page still renders if the API is offline.

**Props down, events up (`App.vue:128-129`)**

```html
<Pet :professionalMode="professionalMode" />
```

`professionalMode` is a prop. The parent owns it; the child reads it. The child does not
mutate it. If the child needed to request a change, it would emit an event and let the
parent update the source of truth. That one-way data flow is what keeps state predictable.

**Contact links (`App.vue:66-125`)**

The links use `target="_blank"` plus `rel="noopener noreferrer"` for external sites.
`noopener` prevents the new page from getting a `window.opener` reference back to your
app; `noreferrer` also suppresses the `Referer` header. The `focus-visible` rings make
keyboard navigation visible without showing a ring on every mouse click.

The resume link is bound to `${API_URL}/api/resume` (`App.vue:112`). The `download`
attribute is a hint; because the API is cross-origin in production, the server's
`Content-Disposition: attachment` header is what reliably triggers the download.

**The `#book` anchor target**

The floating button links to `#book` (`App.vue:165`) and `Pet.vue:76` calls
`document.querySelector('#book')?.scrollIntoView(...)`. The real target is a booking panel
below the pet (`App.vue:131-160`) with `id="book"`, an email CTA, and a resume download.
Putting the target at the bottom makes the sticky CTA produce a visible scroll instead of
jumping to an element that is already on screen. `scroll-mt-24` adds top scroll margin so
the sticky header does not cover the heading, and `html { scroll-behavior: smooth; }` in
`style.css:12-15` animates the jump. The reduced-motion media query immediately below it
restores instant scrolling for users who ask for less motion. The optional chaining in
`Pet.vue` is still useful: if the target is ever removed, the code fails silently instead
of throwing during a successful booking.

### `web/src/components/Pet.vue` - the personality layer

**Props and store wiring (`Pet.vue:6-14`)**

```js
defineProps({ professionalMode: { type: Boolean, default: false } })

const pet = usePetStore()
const { desperation, label, mood, quip, loading, error } = storeToRefs(pet)
```

`storeToRefs` is essential. If you did:

```js
const { desperation } = pet // WRONG
```

you would copy the current number into a plain variable. The UI would never update when the
store changes. `storeToRefs` returns refs that stay connected to the store. Methods and
non-reactive values should be destructured normally; `storeToRefs` is for state/getters.

**Local UI state (`Pet.vue:16-32`)**

- `shooed`: user hid the monkey.
- `menuOpen`: the relief menu is open.
- `cornerIndex`: which safe corner the monkey is in.
- `flipRight`: mirror the sprite toward the cursor.
- `notes`: one draft note per action.
- `activeSprite` / `customQuip`: temporary overrides for mouse reactions.
- `monkeyBtn`: template ref to the button, used for `getBoundingClientRect()`.

**Safe corners (`Pet.vue:35-39`)**

The monkey is `position: fixed` (`Pet.vue:135`) and hops between three corners chosen to
avoid the top navbar and the bottom-right book button. This is a simple constraint system:
enumerate the valid positions instead of computing collision avoidance.

**Computed values (`Pet.vue:41-59`)**

- `meterColor` maps desperation ranges to green, cyan, amber, magenta.
- `speech` uses a priority order: error wins, then temporary mouse quip, then the server's
  quip, then a fallback. This is a tiny decision table; keeping it computed means the
  template stays declarative.
- `currentSprite` uses the temporary override if present, otherwise the store's mood.

**Submitting relief (`Pet.vue:61-72`)**

```js
const data = await pet.interact(type, notes.value[type] || '')
if (!data) return null
if (type in notes.value) notes.value[type] = ''
activeSprite.value = null
customQuip.value = null
menuOpen.value = false
return data
```

On success: clear the note, clear local overrides so the server's fresh mood/quip show,
close the menu. On failure: return early, leave the menu open, and let the store's `error`
appear in the bubble. This is good UX: do not throw away the user's typed note when
validation fails.

**Booking (`Pet.vue:74-77`)**

`bookInterview()` submits a `book` action, then scrolls to `#book` (`Pet.vue:76`). That id
lives on the booking panel below the pet (`App.vue:132`), so a successful booking visibly
scrolls to the email and resume CTAs. The `?.` means the scroll is a progressive
enhancement: if the target is missing, the action still succeeds and nothing crashes.

**Mouse tracking and dodging (`Pet.vue:86-119`)**

```js
const rect = monkeyBtn.value.getBoundingClientRect()
const centerX = rect.left + rect.width / 2
const centerY = rect.top + rect.height / 2
flipRight.value = e.clientX > centerX
const distance = Math.hypot(e.clientX - centerX, e.clientY - centerY)
```

- `getBoundingClientRect()` returns the element's position and size in viewport
  coordinates. Adding half the width/height gives the monkey's center.
- `e.clientX` / `e.clientY` are the cursor position in the viewport. Comparing them to the
  center tells the sprite which way to face.
- `Math.hypot(dx, dy)` is the Euclidean distance: the length of the straight line from
  cursor to monkey. It is the same as `Math.sqrt(dx*dx + dy*dy)` but clearer and avoids
  overflow for huge values.
- If distance `< 85` and `now - lastHopTime > 6000`, the monkey hops and records
  `lastHopTime`. The cooldown prevents the monkey from teleporting on every mouse event.
  Without it, a cursor near the monkey would trigger a hop on every pixel of movement.
- `stopTimer` is cleared before setting a new timeout, so quick movements do not stack
  timers. `onUnmounted` removes the listener and clears the timer, preventing leaks after
  the component disappears.

Analogy: the monkey has personal space (85px) and a refractory period (6 seconds). It is a
simple state machine with hysteresis, which is why it feels alive instead of twitchy.

**Template structure (`Pet.vue:132-259`)**

1. The fixed wrapper hides entirely in professional mode or after "shoo" (`v-if`).
2. The relief menu (`Pet.vue:138-218`) contains the meter and one input/button per action.
3. The speech bubble (`Pet.vue:221-229`) shows `speech`, colored red on error.
4. The sprite (`Pet.vue:232-257`) chooses `/monkey/<mood>.webp` from `public/monkey/` and
   applies animation classes.

**Animations (`Pet.vue:261-304`)**

- `@keyframes breathe` scales and lifts the sleeping monkey.
- `@keyframes floatZ` floats the "Z" letters upward with fading opacity.
- `@keyframes jitter` shakes the anxious monkey in tiny alternating translations.
- `@media (prefers-reduced-motion: reduce)` disables all three. This is an accessibility
  requirement: users who ask their OS to reduce motion should not get infinite animation.
  Note that it only covers these scoped animations; the Tailwind transition classes on the
  meter still animate. For a fully compliant implementation, add a global reduced-motion
  override for transitions as well.

### `web/src/components/HelloWorld.vue`

This is the leftover Vite starter component. Nothing imports it. It is harmless but dead
weight; delete it (and the unused `assets/hero.png`, `vite.svg`, `vue.svg`) when you want a
clean tree. Keeping dead files is not a security problem, but it makes the repo harder to
read and search.

---

## 4. Resume Data Update

`backend/app/resume_data.json` now contains the real details:

- **Education:** `B.Sc. Information Technology`, **Karatina University**, `2022 -
  Expected 2026`, Karatina, Kenya.
- **Experience:** **IT Intern - Judiciary of Kenya** (2025, Nairobi, Kenya), covering
  institutional ICT infrastructure, preventive systems maintenance, and user technical
  support.
- **Experience:** **Backend & AI Engineer - Independent Projects** (2024 - Present),
  covering FastAPI services, Vue/Pinia frontends, and LLM pipeline components.
- **Projects:** **AyuTech**, a full-stack platform using Python/FastAPI, Vue.js/Flet,
  PostgreSQL via Supabase, and M-Pesa Daraja STK Push with callback handling.
- **Projects:** **Find Wachira a Job**, this site, including the deterministic resume
  pipeline.
- **Skills:** added Supabase, Flet, M-Pesa Daraja STK Push, callback handling, and
  third-party APIs.

The PDF is generated from this file, so edit the JSON, not the PDF. The mtime cache means
your next `/api/resume` request automatically picks up the change.

Suggested next step before sending it out: replace the generic Judiciary bullets with
specific numbers or systems you actually touched (for example, "supported 40+ staff
workstations" or "resolved 15 tickets per week"). Specificity beats adjectives.

---

## 5. Things I Must Know for Interviews

### 1. "Walk me through what happens when a user clicks 'Share a link'."

**Strong answer:** The click calls `submitRelief('link')` in `Pet.vue`, which calls the
Pinia `interact()` action with the note. The store sends a cross-origin `POST` with a JSON
body to `${VITE_API_URL}/api/pet/interact`. Because the content type is JSON, the browser
first sends an `OPTIONS` preflight; `CORSMiddleware` approves the origin, then the real
`POST` goes out. FastAPI validates the body with `InteractRequest`, the rate limiter checks
the client IP, and `record_interaction()` takes a lock, updates `pet_state.json`
atomically, and returns the fresh computed state. The store applies the response to its
refs, Vue re-renders, and the meter and sprite update. On `422` or `429`, the store writes a
human-readable error to `error`, and the bubble shows it while the menu stays open.

### 2. "Why use Pydantic instead of checking the request body manually?"

**Strong answer:** Pydantic gives a declarative contract. `Literal` restricts action types,
`Field(max_length=280)` bounds input, `@field_validator` normalizes whitespace, and
`@model_validator` enforces cross-field rules like "link requires a note" and "no
third-party emails in intro notes." FastAPI turns violations into a consistent `422`
response before business logic runs. That means the route only handles valid data, the
error format is standardized, and the rules are testable in isolation. Manual `if`
statements spread the same logic across the route and are easy to forget.

### 3. "Why do you need a lock, and why write to a `.tmp` file first?"

**Strong answer:** Two concurrent POSTs could both read `relief_today = 5`, then write
different results, and one update would be lost. `threading.Lock()` makes load-mutate-save
atomic within the process. The `.tmp` write plus `Path.replace()` is atomic at the
filesystem level, so a crash cannot leave a half-written JSON file; readers see either the
old complete file or the new complete file. The lock handles concurrency, atomic rename
handles crash consistency. They solve different problems and you need both. In a
multi-process or multi-machine deployment, I would move this to a database transaction or
use file locking/Redis, because a Python thread lock does not coordinate across processes.

### 4. "Explain your rate limiter and its production limitations."

**Strong answer:** It is a sliding-window limiter. Each IP has a `deque` of timestamps.
On each request we drop timestamps older than the window, reject if the remaining count is
at the limit, otherwise append the current monotonic timestamp. `time.monotonic()` avoids
wall-clock jumps. `defaultdict(deque)` keeps lookups simple, and `_maybe_sweep()` removes
stale clients once the dictionary reaches 1000 entries so memory does not grow without
bound. The limitation is that the state is in-process: multiple Uvicorn workers each have
their own counter, so the real limit multiplies. In production I would use Redis with an
atomic sorted-set or fixed-window counter shared by all workers. I would also make sure the
proxy forwards the real client IP and configure Uvicorn's trusted proxy headers.

### 5. "Why is the resume generated deterministically instead of by an LLM?"

**Strong answer:** The public download is a factual document, so correctness and
reproducibility matter more than novelty. Storing facts in `resume_data.json` and rendering
with fpdf2 means the same input always produces the same PDF, there is no hallucination
risk, no per-request latency or cost, and changes are reviewable in git. The cache keyed by
file `mtime` avoids rebuilding on every click. If I add AI tailoring, I would keep the
public PDF deterministic: the LLM would only produce a structured, Pydantic-validated
variant from the source data plus a job description, then the same renderer would turn that
variant into a PDF. That keeps the safety boundary in code, not in a prompt.

### 6. "What is CORS and what happens during a preflight?"

**Strong answer:** CORS is a browser security policy that stops JavaScript from one origin
from reading responses from another origin unless the server explicitly allows it. For a
cross-origin `POST` with `Content-Type: application/json`, the browser sends an `OPTIONS`
preflight with `Origin` and `Access-Control-Request-Method`. The server responds with
`Access-Control-Allow-Origin`, `Allow-Methods`, and `Allow-Headers`. If the origin is not
allowed, the browser blocks the actual request and hides the response from JavaScript. In
this app, `CORSMiddleware` allow-lists the Vite dev origins. In production I would add the
deployed frontend origin and keep the list explicit. I would not use `*` with credentials,
and I would remember that CORS is a browser rule, not a substitute for authentication or
server-side authorization.

### 7. "Why a Pinia setup store, and why `storeToRefs`?"

**Strong answer:** The setup store is just a function that returns reactive state and
actions, which makes it easy to compose with Vue's `ref` and `computed`. Pinia unwraps refs
on the store instance for ergonomic access. The trap is destructuring: `const { label } =
pet` copies the value and loses reactivity. `storeToRefs(pet)` returns refs that remain
connected to the store, so template expressions and computed properties update when the
store changes. I use `storeToRefs` for state/getters and destructure actions normally
because actions are stable function references.

### 8. "How would you take this from a demo to production?"

**Strong answer:** Replace the JSON file with PostgreSQL and use migrations (Alembic or
equivalent); move rate-limit counters to Redis so they are shared across workers; add
authentication/authorization for any admin or write endpoints; add structured logging,
request IDs, and error tracking; add tests for the validation rules, the meter formula, the
limiter, and the resume cache; containerize the backend and frontend; add health/readiness
checks; configure the production CORS origin and HTTPS; manage secrets outside the repo;
and add CI that runs tests and builds. I would also delete the unused scaffold files and
decide whether booking an interview should reset `last_interview_at`. The goal is not more
technology; it is making failures observable and making the safe path the easy path.

---

## 6. Official Reading List

Skim these in order. You do not need to memorize them; you need to recognize the concepts
when an interviewer uses the terminology.

### FastAPI

- Tutorial index: <https://fastapi.tiangolo.com/tutorial/>
- Request body and Pydantic models: <https://fastapi.tiangolo.com/tutorial/body/>
- CORS: <https://fastapi.tiangolo.com/tutorial/cors/>
- Dependencies (the next step after this project): <https://fastapi.tiangolo.com/tutorial/dependencies/>
- Response model and return types: <https://fastapi.tiangolo.com/tutorial/response-model/>

### Pydantic validators

- Validators overview: <https://docs.pydantic.dev/latest/concepts/validators/>
- Fields and constraints: <https://docs.pydantic.dev/latest/concepts/fields/>
- Models and type coercion: <https://docs.pydantic.dev/latest/concepts/models/>

### Pinia setup stores

- Core concepts, including setup stores: <https://pinia.vuejs.org/core-concepts/>
- State and `storeToRefs`: <https://pinia.vuejs.org/core-concepts/state/>
- Actions: <https://pinia.vuejs.org/core-concepts/actions/>

### Vue 3 reactivity

- Reactivity fundamentals: <https://vuejs.org/guide/essentials/reactivity-fundamentals.html>
- Computed properties: <https://vuejs.org/guide/essentials/computed.html>
- Lifecycle hooks: <https://vuejs.org/guide/essentials/lifecycle.html>
- `v-if` / conditional rendering: <https://vuejs.org/guide/essentials/conditional.html>

### CORS and web security

- MDN CORS guide: <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>
- MDN preflight request: <https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request>

### OWASP LLM Top 10

- Official project page: <https://genai.owasp.org/llm-top-10/>
- OWASP Top 10 for LLM Applications (project page): <https://owasp.org/www-project-top-10-for-large-language-model-applications/>

Pay special attention to LLM01 (prompt injection), LLM02 (sensitive information
disclosure), LLM05 (improper output handling), and LLM06 (excessive agency). Those four are
the ones most likely to matter when you add resume tailoring or any model-driven feature.

---

## Final Mental Model

If you remember only one paragraph, remember this:

> The browser is a dining room, Pinia is the shared order pad, FastAPI is the kitchen,
> rate limiting is the bouncer, and JSON files are the pantry. A GET asks a question; a
> POST changes the kitchen's state. CORS is the border checkpoint that decides whether the
> browser is allowed to read the answer. The resume is printed from a structured source of
> truth, not improvised, so the facts stay reproducible. Vue's reactivity is what makes the
> meter move without manually touching the DOM, and the thread lock plus atomic rename are
> what keep concurrent clicks from corrupting the pantry.

That is the whole system. You built it, and now you can explain it.
