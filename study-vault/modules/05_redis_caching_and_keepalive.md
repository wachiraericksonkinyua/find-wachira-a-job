# Module 05 — Keep-Alive, Render/Supabase Warmth, and Redis Caching

**Days covered:** operations / after Day 44

## The one-sentence version

Keep a free deployment warm with a cheap scheduled request that also touches the
database, and add Redis only when you need shared, multi-instance, or
restart-safe caching/rate limiting.

## 1. Why free services go to sleep

- **Render free web services** spin down after a period of inactivity and cold
  start on the next request.
- **Supabase free projects** can be paused after about 7 days of low activity.
- A UI-only ping is not enough if you want the database awake: the request must
  actually run a query.

This repository now exposes:

```http
GET /api/keepalive
```

When Postgres is configured it runs `SELECT 1`, then returns:

```json
{ "status": "ok", "database": "postgres", "checked_at": "..." }
```

When no database is configured it reports `"database": "json-fallback"` and
still returns HTTP 200.

## 2. How to schedule the keep-alive

### Option A — GitHub Actions

Set the repository secret:

```text
BACKEND_HEALTH_URL=https://your-service.onrender.com/api/keepalive
```

The workflow `.github/workflows/keepalive.yml` runs every 10 minutes and also
supports manual `workflow_dispatch`.

**Caveat:** GitHub scheduled workflows are not guaranteed to run exactly on
time. For a strict Render free-tier keep-alive, use an external monitor too.

### Option B — External uptime monitor

Create a free monitor pointing at:

```text
https://your-service.onrender.com/api/keepalive
```

Check every 5–10 minutes:

- UptimeRobot
- cron-job.org
- Better Stack Uptime

### Option C — Pay for always-on

Render paid instances and Supabase Pro remove the sleep/pause behavior. This is
the simplest production answer if the site must be reliably online 24/7.

## 3. Why this project does not use Redis yet

Current caching/persistence choices:

- Excuse Buster uses an **in-process TTL cache** keyed by `(excuse_id, resume_mtime)`.
- Embeddings use a **JSON cache** plus optional pgvector/Postgres.
- Content (bookings, roasts, board, projects, reactions, logs) uses
  **PostgreSQL when configured**, otherwise atomic JSON fallbacks.
- Rate limiting uses a **per-process sliding-window limiter**.

That is enough for a single Render instance. Redis would add another service,
network latency, and another failure mode without a clear win at this scale.

### Redis becomes worth it when

- multiple backend instances share rate limits or sessions
- expensive LLM responses must survive restarts and be shared across workers
- you need queues/background jobs (Celery, RQ, BullMQ)
- you need pub/sub, websockets fan-out, or presence
- hot leaderboards/trending counters need fast atomic increments
- distributed locks or idempotency keys are required

### Sensible Redis patterns to learn

- **Cache-aside:** read cache → miss → read DB → write cache with TTL
- **Rate limiting:** `INCR` + `EXPIRE` or a Lua script for atomic windows
- **TTL discipline:** always set an expiry; never let stale data live forever
- **Cache invalidation:** update/delete the cache key when the source changes
- **Failure policy:** if Redis is down, fall back to the database, not to a crash

## 4. Official reading (verified 2026-11-07)

- [Redis documentation](https://redis.io/docs/latest/)
- [Redis caching patterns overview](https://redis.io/docs/latest/develop/use/patterns/)
- [Redis client-side caching](https://redis.io/docs/latest/develop/use/client-side-caching/)
- [redis-py client docs](https://redis.io/docs/latest/develop/clients/redis-py/)
- [redis-py GitHub repository](https://github.com/redis/redis-py)
- [Redis University](https://university.redis.io/)
- [Upstash Redis getting started](https://upstash.com/docs/redis/overall/getstarted)
- [Render free tier behavior](https://render.com/docs/free)
- [Render Key Value (Redis-compatible)](https://render.com/docs/key-value)
- [Supabase production checklist](https://supabase.com/docs/guides/platform/going-into-prod) — includes the 7-day free-plan pause note
- [GitHub Actions `schedule` syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [UptimeRobot](https://uptimerobot.com/)
- [cron-job.org](https://cron-job.org/en/)
- [Better Stack Uptime](https://betterstack.com/uptime)
- [FastAPI lifespan events](https://fastapi.tiangolo.com/advanced/events/)

## 5. Practice checklist

- [ ] Open `/api/keepalive` locally and confirm the JSON shape.
- [ ] Deploy, set `BACKEND_HEALTH_URL`, and run the workflow manually.
- [ ] Confirm the Supabase dashboard shows recent activity after the keep-alive.
- [ ] Explain why `/health` is not enough to keep the database active.
- [ ] Draw the cache-aside flow for an expensive RAG response.
- [ ] Write the Redis key naming scheme you would use for:
  - `excuse:{id}:{resume_mtime}`
  - `ratelimit:{route}:{ip}`
  - `job:{job_id}:draft`
- [ ] Decide when you would delete or invalidate each key.
- [ ] Explain what happens when Redis is unreachable.

## 6. 10-minute drill

Add a tiny local test that starts a fake Redis connection failure, confirms the
application still reads from Postgres/JSON, and writes down the fallback policy.
The correct behavior is **degrade, not crash**.
