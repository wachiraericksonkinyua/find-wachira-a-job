from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.pet import InteractRequest, compute_state, load_state, record_interaction
from app.rate_limit import interact_limiter

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
