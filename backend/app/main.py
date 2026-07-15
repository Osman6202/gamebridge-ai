"""GameBridge AI — Backend entry point (FastAPI).

This is the scaffold for Week 1+. The core modules (auth, projects, test runner,
diagnostics, verification) are added incrementally. The health endpoint lets the
container/orchestrator confirm the service is up before the AI layer exists.
"""

from fastapi import FastAPI

app = FastAPI(title="GameBridge AI", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "phase": "core-scaffold"}


# Routers are mounted as modules land (see app/api/routes/).
# import app.api.routes.*  # uncomment as each module is implemented


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
