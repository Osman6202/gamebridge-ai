# Xsolla application answer

**Question:** "What's something hard you built recently, and why did you build it?"

> I built **GameBridge AI**, a game-commerce API debugger that runs deterministic
> integration tests, uses a local LLM to diagnose failures with cited evidence, then
> *re-verifies* every suggested fix by re-running the test — a fix is only marked
> "verified" when the integration actually turns green. I built it because Xsolla's
> customers are game developers who live in this exact problem space, and I wanted to
> prove AI diagnosis can be **verified, not just asserted**: I ship an eval harness that
> measures root-cause accuracy (~92% across 13 failure modes) instead of hoping the model
> was right. It's 100% local/free (Ollama) and deployed-ready.

Copy the paragraph above into the Xsolla application form (or record the 2-min version per
`docs/demo-guide.md`).
