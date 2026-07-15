# GameBridge AI

> AI-powered game-commerce API integration, diagnosis, and verification platform.

GameBridge AI tests game-commerce API integrations (auth, catalog, orders, webhooks),
uses AI to **diagnose** failures with evidence, and **verifies** the suggested fix by rerunning a
deterministic automated test. AI suggestions are not considered successful until a test proves them.

Built as a portfolio centerpiece for the **Xsolla AI-First Engineering Intern** application.
Xsolla is a game-commerce / monetization company — this tool operates in that exact problem space.

## Core principle

> AI suggestions are not verified until an automated verification test passes.

This is the whole point: the AI explains *what* broke and *why*, proposes a fix, but the system
only marks it "verified" when the real integration test turns green. No trust without evidence.

## Stack

- **Frontend:** React + TypeScript + Vite + Tailwind
- **Backend:** FastAPI + Pydantic + SQLAlchemy
- **Mock Commerce API:** FastAPI (controlled success + 15 failure modes)
- **DB:** SQLite (dev + MVP deploy)
- **LLM:** Pluggable `LLMProvider` — default **local/free** (Ollama or `hy3:free`), Claude optional
- **Tests:** Pytest + Playwright
- **Deploy:** Docker Compose / Vercel + Render or Railway

## Architecture

```
Developer → React Frontend → FastAPI Backend
                              ├─ Test Runner → Mock Commerce API (failure injection)
                              ├─ Trace + Redaction
                              ├─ Diagnostic Service → LLMProvider (local/free)
                              └─ Verification Engine → reruns test → verified/unverified
```

## Local setup

```bash
docker compose up --build
# or manually: see backend/README and frontend/README
```

## Build status

See the 21-day plan in `docs/build-plan.md`. Current phase: **Week 1 — Core platform (no AI)**.

## What's built vs deferred

**MVP (shipping):** auth, project CRUD, mock API + 15 failures, test runner, tracing, redaction,
AI diagnosis (local/free), RAG retrieval, verification engine, reports, 15 eval scenarios, CI, deploy.

**Deferred:** OpenAPI import, Unity client, team workspaces, pgvector/PostgreSQL, real Xsolla sandbox
calls, PDF reports.

## AI-assisted development disclosure

AI coding tools scaffolded components, reviewed choices, and generated test ideas. Every accepted
change was verified with unit/integration/E2E tests or runtime inspection. In-product AI diagnoses
are treated as unverified until the related deterministic test passes.

## License

MIT
