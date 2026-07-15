# Demo video + screenshots — recording guide

The README references a 2-minute demo video and screenshots for the Xsolla application.
This is a **manual** step (needs a browser + screen recorder). Exact script below.

## Prerequisites (one time)
1. Start backend + mock (see README "Local setup").
2. Start Ollama with `qwen2.5:3b` (for live AI diagnosis in the recording).
3. `cd frontend && npm run dev` → open http://localhost:5173.

## Screenshots to capture (PNG, full window)
1. `dashboard.png` — Dashboard with one project, "How GameBridge works" expanded.
2. `test-fail.png` — Test Runner after running "Create order with missing sku" (shows 400 trace).
3. `diagnose.png` — after "Diagnose with AI" (root cause + evidence + confidence).
4. `fix.png` — after "Suggest Fix" (code + verification test).
5. `verify.png` — after "Verify" (verified / unverified badge).

## 2-minute demo script (voiceover optional)
- 0:00–0:20 — "GameBridge tests game-commerce API integrations. Here's a failing order call
  (missing SKU → 400). The trace is captured and secrets are redacted."
- 0:20–0:50 — "Click Diagnose. A local LLM reads the real request/response + API docs and
  returns the root cause with evidence and a confidence score — no cloud, no cost."
- 0:50–1:30 — "It proposes a fix with a verification test. Now the critical part: we re-run that
  test. The fix is only marked VERIFIED if the integration actually passes."
- 1:30–2:00 — "That's the thesis — AI diagnosis you can verify, not just trust. 92% root-cause
  accuracy across 13 failure modes, measured by the shipped eval harness."

## Record
Use OBS / QuickTime / Windows Game Bar. Crop to the browser window. Export `demo.mp4`
(≤ 2 min, ≤ 50 MB) and link it from the README and the Xsolla application.
