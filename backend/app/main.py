"""GameBridge AI — Backend entry point (FastAPI)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.models import *  # noqa: F401,F403 — register all models
from app.api.routes import auth, projects, tests

app = FastAPI(title="GameBridge AI", version="0.3.0")

# CORS: frontend (Vite dev :5173, deployed Vercel) talks to this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to known origins on real deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables (dev/MVP). Production would use Alembic migrations.
Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(tests.router)


@app.get("/health")
async def health():
    return {"status": "ok", "phase": "core-auth-projects"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
