import logging
import os
import secrets
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.apply_assistant import (
    AnalyzeRequest,
    DraftRequest,
    JobStatusUpdate,
    analyze_job,
    draft_application,
    list_jobs,
    update_job_status,
)
from app import content_store
from app.board import (
    BoardSubmission,
    EventRequest,
    TakedownRequest,
    admin_entries,
    admin_stats,
    approve_entry,
    list_approved,
    record_event,
    reject_entry,
    submit_entry,
    takedown_entry,
)
from app.bookings import (
    BookingRequest,
    get_bookings,
    get_pet_leads,
    record_pet_lead,
    save_booking,
)
from app.embeddings import _connect_postgres, postgres_available
from app.projects import get_project, iter_project_chunks, load_projects
from app.excuses import PRESET_EXCUSES, ExcuseRequest
from app.llm import (
    InterrogateRequest,
    configured_providers,
    stream_excuse_buster,
    stream_inspect_project,
    stream_interrogation,
    stream_judgment,
)
from app.match import MatchRequest, MatchResponse, run_match
from app.pet import InteractRequest, compute_state, load_state, record_interaction
from app.portfolio import (
    ProjectAdminCreate,
    ProjectAdminUpdate,
    ProjectReaction,
    create_project,
    delete_project,
    list_admin_projects,
    update_project,
)
from app.roasts import (
    RoastModeration,
    RoastSubmission,
    admin_roasts,
    approve_roast,
    delete_roast,
    public_roasts,
    reject_roast,
    submit_roast,
)
from app.rate_limit import (
    analytics_limiter,
    apply_limiter,
    board_limiter,
    interact_limiter,
    llm_limiter,
    redteam_limiter,
)
from app.redteam import (
    AttackRequest,
    FlagSubmission,
    get_leaderboard as get_redteam_leaderboard,
    list_levels as list_redteam_levels,
    run_attack as run_redteam_attack,
    security_report as build_security_report,
    submit_flag as submit_redteam_flag,
)
from app.resume import load_resume_data, render_resume_pdf

logger = logging.getLogger(__name__)

app = FastAPI(title="Find Wachira a Job API", version="0.1.0")

LOCAL_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]


def allowed_origins() -> list[str]:
    """Local dev origins plus any comma-separated production domains.

    ``ALLOWED_ORIGINS`` is optional: when unset, only the local Vite origins
    are trusted, so a misconfigured deploy never falls back to ``*``.
    """
    origins = list(LOCAL_DEV_ORIGINS)
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(","):
        origin = origin.strip().rstrip("/")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin_key(x_admin_key: str | None) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin key is not configured.")
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin key.")

REQUEST_LOGS: deque[dict] = deque(maxlen=100)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    REQUEST_LOGS.append(
        {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    response.headers["X-Request-ID"] = request_id
    return response


SECURITY_CONTROLS = [
    "OWASP-LLM01-Untrusted-Delimiters",
    "Server-Attached-RAG-Citations",
    "Sliding-Window-Rate-Limit",
    "Timing-Safe-Admin-Auth",
    "Isolated-Red-Team-CTF-Sandbox",
    "Moderated-Peer-Talent-Board",
    "SSRF-Private-IP-Block",
    "Human-in-the-Loop-Apply-Assistant",
]


@app.get("/health")
async def health_check():
    return {"status": "ok", "db": True}


@app.get("/api/keepalive")
def keepalive():
    """Touch the database so Render and Supabase stay warm/active.

    `/health` is intentionally dependency-free. This endpoint performs the
    smallest useful Postgres query, so an external scheduler can keep both the
    web service and the free Supabase project from going idle.
    """
    connection = _connect_postgres()
    if connection is None:
        return {
            "status": "ok",
            "database": "json-fallback",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        logger.warning("Keepalive database query failed (%s).", exc)
        raise HTTPException(
            status_code=503, detail="Database keepalive query failed."
        ) from None
    finally:
        connection.close()

    return {
        "status": "ok",
        "database": "postgres",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/telemetry")
def telemetry():
    return {
        "status": "ok",
        "vector_store": "pgvector" if postgres_available() else "local_json",
        "indexed_chunks": sum(1 for _ in iter_project_chunks()),
        "llm_providers": configured_providers(),
        "security_controls": SECURITY_CONTROLS,
    }


@app.get("/api/resume")
def resume_pdf():
    # Deterministic render from resume_data.json: the public download cannot
    # invent experience the way a live LLM generation call could.
    pdf = render_resume_pdf()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="wachira-erickson-kinyua-resume.pdf"',
        },
    )


@app.get("/api/resume.json")
def resume_json():
    # The same structured source used by the PDF renderer, ready for future
    # per-job tailoring without scraping the PDF.
    return load_resume_data()


@app.get("/api/projects")
def projects():
    return load_projects()


@app.get("/api/projects/{project_id}/inspect")
async def inspect_project(project_id: str, request: Request):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client_ip = request.client.host if request.client else "unknown"
    if not llm_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests! Monkey is tired.")

    return StreamingResponse(
        stream_inspect_project(project),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/pet/state")
def pet_state():
    # Sync route: FastAPI runs this in its threadpool, so file I/O
    # does not block the event loop.
    return compute_state(load_state())


@app.post("/api/pet/interact")
def pet_interact(payload: InteractRequest, request: Request):
    # Behind a proxy this is the proxy's IP; uvicorn's --proxy-headers
    # setting lets FastAPI use the real client IP safely in production.
    client_ip = request.client.host if request.client else "unknown"

    if not interact_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many interactions! Let the monkey breathe a bit.",
        )

    # Pydantic has already validated and cleaned the body by now.
    pet_state = record_interaction(payload.type, payload.note)
    record_pet_lead(payload.type, payload.note)
    return pet_state


@app.post("/api/book")
def book_interview(payload: BookingRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not interact_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many bookings! Give the monkey a moment.",
        )

    booking = save_booking(payload)
    pet_state = record_interaction(
        "book", f"{payload.name} ({payload.company or 'Direct'})"
    )
    return {"booking": booking, "pet_state": pet_state}


@app.get("/api/admin/leads")
def admin_leads(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return {"bookings": get_bookings(), "pet_leads": get_pet_leads()}


@app.get("/api/llm/status")
def llm_status():
    # Never return the keys themselves, only which providers are ready.
    return {"providers": configured_providers()}


@app.get("/api/pet/judgment")
async def pet_judgment(
    request: Request,
    action: str = Query(default="scroll_projects", max_length=40),
    context: str | None = Query(default=None, max_length=500),
):
    # Stream the model's tokens as Server-Sent Events. The generator handles
    # provider fallback and emits its own local fallback when no key is set,
    # because HTTP headers cannot be changed once streaming has started.
    client_ip = request.client.host if request.client else "unknown"

    if not llm_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many judgments! The monkey needs a breather.",
        )

    return StreamingResponse(
        stream_judgment(action, context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/recruiter/interrogate")
async def recruiter_interrogate(payload: InterrogateRequest, request: Request):
    # Stream a grounded verdict on the pasted JD. The JD is capped and wrapped
    # as untrusted data in llm.py before it reaches the model.
    client_ip = request.client.host if request.client else "unknown"

    if not llm_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many interrogations! Give the monkey time to read.",
        )

    return StreamingResponse(
        stream_interrogation(payload.company, payload.role, payload.jd),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/match", response_model=MatchResponse)
def match_role(payload: MatchRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    if not llm_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many match requests! Give the monkey a moment.",
        )

    return run_match(payload)


@app.get("/api/excuses")
def get_excuses():
    return [{"id": id, "text": text} for id, text in PRESET_EXCUSES.items()]


@app.post("/api/excuse-buster")
async def excuse_buster(payload: ExcuseRequest, request: Request):
    from app.resume import DATA_FILE
    
    client_ip = request.client.host if request.client else "unknown"
    if not llm_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests! Monkey is tired.",
        )
        
    if payload.excuse_id not in PRESET_EXCUSES:
        raise HTTPException(status_code=422, detail="Unknown excuse ID")
    
    mtime = DATA_FILE.stat().st_mtime
    
    return StreamingResponse(
        stream_excuse_buster(payload.excuse_id, mtime),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/redteam/levels")
def redteam_levels():
    # Level metadata only: flags live server-side in app/redteam.py.
    return list_redteam_levels()


@app.post("/api/redteam/attack/{level}")
def redteam_attack(level: int, payload: AttackRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not redteam_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many attacks! Let the sandbox cool down for a minute.",
        )

    try:
        return run_redteam_attack(level, payload.prompt, client_ip)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown red-team level") from None


@app.post("/api/redteam/submit")
def redteam_submit(payload: FlagSubmission):
    try:
        return submit_redteam_flag(payload.level, payload.guess, payload.nickname)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown red-team level") from None


@app.get("/api/redteam/leaderboard")
def redteam_leaderboard():
    return get_redteam_leaderboard()


@app.get("/api/security/report")
def security_report():
    return build_security_report()

@app.post("/api/events", status_code=204)
def submit_event(payload: EventRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not analytics_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many analytics events.")
    record_event(payload)
    return Response(status_code=204)


@app.get("/api/admin/stats")
def admin_stats_view(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return admin_stats()


@app.get("/api/board")
def get_board():
    return list_approved()


@app.post("/api/board/submit")
def submit_board_entry(payload: BoardSubmission, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not board_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many board submissions.")
    return submit_entry(payload)


@app.post("/api/board/takedown")
def takedown_board_entry(payload: TakedownRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not board_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many takedown requests.")
    try:
        return takedown_entry(payload.id, payload.token)
    except KeyError:
        raise HTTPException(status_code=404, detail="Board entry not found.") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Invalid takedown token.") from None


@app.post("/api/admin/board/{entry_id}/approve")
def approve_board_entry(
    entry_id: str,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    try:
        return approve_entry(entry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Board entry not found.") from None


@app.post("/api/apply/analyze")
def apply_analyze(payload: AnalyzeRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not apply_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many apply-assistant requests.")

    try:
        return analyze_job(payload.url, payload.raw_jd)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@app.post("/api/apply/draft")
def apply_draft(payload: DraftRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not apply_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many draft requests.")

    try:
        return draft_application(
            job_id=payload.job_id,
            url=payload.url,
            raw_jd=payload.raw_jd,
            title=payload.title,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Tracked job not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None


@app.get("/api/apply/jobs")
def apply_jobs():
    return list_jobs()


@app.put("/api/apply/jobs/{job_id}")
def apply_job_status(job_id: str, payload: JobStatusUpdate):
    try:
        return update_job_status(job_id, payload.status)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tracked job not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@app.get("/api/roasts")
def get_roasts():
    return public_roasts()


@app.post("/api/roasts")
def create_roast(payload: RoastSubmission, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    if not board_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many roast submissions.")
    return submit_roast(payload)


@app.get("/api/admin/roasts")
def get_admin_roasts(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return admin_roasts(status)


@app.post("/api/admin/roasts/{roast_id}/approve")
def approve_roast_route(
    roast_id: str,
    payload: RoastModeration | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    try:
        return approve_roast(roast_id, payload.note if payload else "")
    except KeyError:
        raise HTTPException(status_code=404, detail="Roast not found.") from None


@app.post("/api/admin/roasts/{roast_id}/reject")
def reject_roast_route(
    roast_id: str,
    payload: RoastModeration | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    try:
        return reject_roast(roast_id, payload.note if payload else "")
    except KeyError:
        raise HTTPException(status_code=404, detail="Roast not found.") from None


@app.delete("/api/admin/roasts/{roast_id}")
def delete_roast_route(
    roast_id: str,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    if not delete_roast(roast_id):
        raise HTTPException(status_code=404, detail="Roast not found.")
    return {"deleted": True, "id": roast_id}


@app.get("/api/admin/board")
def get_admin_board(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected)$"),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return admin_entries(status)


@app.post("/api/admin/board/{entry_id}/reject")
def reject_board_entry(
    entry_id: str,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    try:
        return reject_entry(entry_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Board entry not found.") from None


@app.get("/api/admin/projects")
def get_admin_projects(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return list_admin_projects()


@app.post("/api/admin/projects")
def create_admin_project(
    payload: ProjectAdminCreate,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return create_project(payload)


@app.put("/api/admin/projects/{project_id}")
def update_admin_project(
    project_id: str,
    payload: ProjectAdminUpdate,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    try:
        return update_project(project_id, payload)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found.") from None


@app.delete("/api/admin/projects/{project_id}")
def delete_admin_project(
    project_id: str,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    if not delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"deleted": True, "id": project_id}


@app.get("/api/admin/logs")
def get_admin_logs(
    limit: int = Query(default=100, ge=1, le=500),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    require_admin_key(x_admin_key)
    return content_store.list_admin_logs(limit=limit)


@app.post("/api/projects/{project_id}/reactions")
def react_to_project(
    project_id: str,
    payload: ProjectReaction,
    request: Request,
):
    client_ip = request.client.host if request.client else "unknown"
    if not board_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many project reactions.")
    if not get_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    try:
        return content_store.record_reaction(project_id, payload.reaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


def _limiter_snapshot(name: str, limiter) -> dict[str, int | str]:
    return {
        "name": name,
        "max_requests": limiter.max_requests,
        "window_seconds": limiter.window_seconds,
        "active_clients": len(limiter._hits),
    }


@app.get("/api/system/logs")
def system_logs():
    from app.rate_limit import (
        analytics_limiter,
        apply_limiter,
        board_limiter as board_limiter_ref,
        interact_limiter,
        llm_limiter,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": {
            "status": "ok",
            "database": "postgres" if postgres_available() else "json-fallback",
        },
        "vector_store": "pgvector" if postgres_available() else "local_json",
        "indexed_chunks": sum(1 for _ in iter_project_chunks()),
        "llm_providers": configured_providers(),
        "security_controls": SECURITY_CONTROLS,
        "rate_limits": [
            _limiter_snapshot("llm", llm_limiter),
            _limiter_snapshot("interact", interact_limiter),
            _limiter_snapshot("redteam", redteam_limiter),
            _limiter_snapshot("analytics", analytics_limiter),
            _limiter_snapshot("board", board_limiter_ref),
            _limiter_snapshot("apply", apply_limiter),
        ],
        "requests": list(REQUEST_LOGS)[-50:],
    }
