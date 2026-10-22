from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.llm import LLMError, configured_providers, generate_judgment
from app.pet import InteractRequest, compute_state, load_state, record_interaction
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
def pet_judgment(
    request: Request,
    action: str = Query(default="scroll_projects", max_length=40),
    context: str | None = Query(default=None, max_length=500),
):
    # This is the non-streaming LLM client from Day 7. Day 8 upgrades the same
    # data path to Server-Sent Events for the Judgment Box.
    client_ip = request.client.host if request.client else "unknown"

    if not llm_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many judgments! The monkey needs a breather.",
        )

    if not configured_providers():
        raise HTTPException(
            status_code=503,
            detail="No LLM key configured. Set GROQ_API_KEY or GEMINI_API_KEY in backend/.env.",
        )

    try:
        reply = generate_judgment(action, context)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "commentary": reply.text,
        "provider": reply.provider,
        "model": reply.model,
    }
