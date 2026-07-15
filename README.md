# GameBridge AI

> An AI-powered game-commerce API debugger that proves AI-assisted diagnosis can be **verified, not just asserted**.

GameBridge runs deterministic integration tests against a game-commerce API (or the bundled mock), uses a local/free LLM to **diagnose** failures with cited evidence, proposes a fix, and then **re-verifies** the fix by re-running the test. A fix is only marked **verified** when a real automated test turns green.

Built as the portfolio centerpiece for the **Xsolla AI-First Engineering Intern** application. Xsolla is a game-commerce / monetization company — GameBridge operates in that exact problem space.

---

## The core thesis

> An AI suggestion is not trusted until a deterministic test proves it.

The LLM explains *what* broke and *why* (with evidence from the real request/response trace + API docs) and proposes a fix — but the system only marks it **verified** when the integration test actually passes. No blind trust in model output. This directly answers the question Xsolla asks: *"How did you confirm the AI actually worked?"*

---

## Architecture

```
Developer
   │
   ▼
React + TS Frontend  ──(REST)──▶  FastAPI Backend
                                    │
                    ┌───────────────┼───────────────────────┐
                    ▼               ▼                        ▼
              Test Runner      Diagnostic Service        Verification Engine
              (15 failure      (LLMProvider:             (re-runs the fix's
               modes vs mock)   Ollama / hy3:free)        verification test)
                    │               │                        │
                    ▼               ▼                        ▼
              Request Trace   Diagnosis (root_cause,   verified / unverified
              + Secret         evidence, confidence)   (deterministic, honest)
                Redaction  ◀── docs retrieval (FTS5)
```

- **Frontend:** React + TypeScript + Vite
- **Backend:** FastAPI + Pydantic + SQLAlchemy (SQLite for dev/MVP)
- **Mock Commerce API:** FastAPI with 15 controlled failure modes (auth, catalog, orders, webhooks)
- **LLM:** Pluggable `LLMProvider`. Default = **100% local/free** (Ollama `qwen2.5:3b`, no API key, no cost). Optional: Hermes local gateway (`hy3:free`) via `HERMES_API_KEY`.
- **Retrieval:** SQLite FTS5 — real keyword search over API docs, zero new dependencies.
- **Tests:** Pytest (25 backend tests), evaluation harness (`app.eval.run`).

---

## What's built (MVP — shipped)

| Capability | Status |
|---|---|
| JWT auth + project CRUD + owner isolation | ✅ |
| Mock Commerce API with 15 failure modes | ✅ |
| Test runner → deterministic integration tests | ✅ |
| Request tracing **with secret redaction before storage + LLM** | ✅ |
| Webhook receiver with constant-time HMAC + duplicate rejection | ✅ |
| Local doc store (FTS5) + retrieval | ✅ |
| AI diagnosis (root cause + evidence + confidence) | ✅ |
| Suggested fixes (code + verification test) | ✅ |
| **Verification engine** (fix verified only after test re-run) | ✅ |
| Full clickable UI: run → diagnose → fix → verify | ✅ |
| Evaluation harness across all failure modes | ✅ |
| Deploy configs (Render ×2, Railway) | ✅ |

---

## Evaluation — did the AI actually work?

Run with `python -m app.eval.run` (Ollama on CPU). Across **13 real diagnosis targets** (every failing integration scenario):

- **Root-cause accuracy: 12 / 13 correct (~92%)**, average confidence **0.99**.
- One genuine weakness: a **duplicate-webhook** event is occasionally mislabeled as a signature problem (the mock's receiver validates the signature before the duplicate check, so the trace shows a 401). Documented, not hidden.
- Prompt-injection guard: trace/document content is treated as untrusted data, never as instructions.

These numbers are produced by an automated harness, not asserted by hand — the repo ships the script that regenerates them.

---

## Local setup

```bash
# 1. Start the mock + backend (backend on :8000, mock on :8001)
cd backend
pip install -r requirements.txt
# terminal A:
uvicorn app.main:app --host 127.0.0.1 --port 8000
# terminal B:
cd ../mock_service && uvicorn app.main:app --host 127.0.0.1 --port 8001

# 2. (optional) AI diagnosis — install Ollama and pull the model:
ollama pull qwen2.5:3b      # default; no key, no cost
# or set HERMES_API_KEY to use the Hermes local gateway instead

# 3. Frontend
cd ../frontend && npm install && npm run dev   # http://localhost:5173

# 4. Run the test suite
cd ../backend && pytest -q

# 5. Run the evaluation harness
python -m app.eval.run
```

Without an LLM reachable, every non-AI feature works; diagnosis endpoints return a clear "LLM not configured" marker instead of failing.

---

## AI-assisted development disclosure

AI coding tools scaffolded components, reviewed choices, and generated test ideas. Every accepted change was verified with unit/integration tests or runtime inspection. In-product AI diagnoses are treated as **unverified until the related deterministic test passes** — the same standard the product enforces.

## License

MIT
