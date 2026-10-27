from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.projects import Project, load_projects
from app.excuses import PRESET_EXCUSES, ExcuseRequest
from app.llm import (
    InterrogateRequest,
    configured_providers,
    stream_excuse_buster,
    stream_inspect_project,
    stream_interrogation,
    stream_judgment,
)
from app.pet import InteractRequest, compute_state, load_state, record_interaction
from app.projects import get_project, load_projects
from app.rate_limit import interact_limiter, llm_limiter
from app.resume import load_resume_data, render_resume_pdf

app = FastAPI(title="Find Wachira a Job API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": True}


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
    return record_interaction(payload.type, payload.note)


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

@app.get("/api/projects", response_model=list[Project])
def projects():
    return load_projects()