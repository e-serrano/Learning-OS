from fastapi import FastAPI

from app.api.onboarding import router as onboarding_router

app = FastAPI(title="Learning OS API", version="0.1.0")
app.include_router(onboarding_router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
