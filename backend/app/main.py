from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.onboarding import router as onboarding_router

app = FastAPI(title="Learning OS API", version="0.1.0")

# Local-only: the UI dev server runs on a different loopback port. Never add
# non-loopback origins here -- see docs/AGENTS.md #19 / docs/API_SPEC.md #12.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
