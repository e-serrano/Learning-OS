from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.assessments import router as assessments_router
from app.api.diagnostic import router as diagnostic_router
from app.api.goals import router as goals_router
from app.api.knowledge import router as knowledge_router
from app.api.onboarding import router as onboarding_router
from app.api.progress import router as progress_router
from app.api.projects import router as projects_router
from app.api.providers import router as providers_router
from app.api.reviews import router as reviews_router
from app.api.roadmap import router as roadmap_router
from app.api.sandbox import router as sandbox_router
from app.api.sessions import router as sessions_router
from app.api.settings import router as settings_router
from app.api.teach_back import router as teach_back_router
from app.api.vault import router as vault_router

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
app.include_router(goals_router)
app.include_router(vault_router)
app.include_router(providers_router)
app.include_router(knowledge_router)
app.include_router(roadmap_router)
app.include_router(diagnostic_router)
app.include_router(sessions_router)
app.include_router(reviews_router)
app.include_router(assessments_router)
app.include_router(teach_back_router)
app.include_router(projects_router)
app.include_router(progress_router)
app.include_router(settings_router)
app.include_router(sandbox_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
