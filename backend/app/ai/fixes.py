"""Suggested-fix generation (Day 12)."""

from sqlalchemy.orm import Session
from typing import Optional

from app.ai.provider import complete_json, LLMConfig
from app.models import Diagnosis, SuggestedFix

FIX_SYSTEM = """You are a senior backend engineer. Given a diagnosis of a failed game-commerce
API integration test, propose concrete fixes the developer can apply.

Output ONLY a JSON array of objects, each:
{
  "fix_type": "code" | "configuration" | "documentation",
  "description": string,            // what to change
  "code": string | null,            // example snippet if code fix
  "verification_test": string       // which existing test should now pass, e.g. "Create order with valid token"
}

Order by priority. Be specific and correct. No markdown fences."""


async def suggest_fixes_for(
    db: Session,
    diagnosis_id: int,
    config: Optional[LLMConfig] = None,
) -> list[SuggestedFix]:
    diag = db.get(Diagnosis, diagnosis_id)
    if diag is None:
        raise ValueError("diagnosis_not_found")

    user = f"""PROBLEM: {diag.problem}
ROOT CAUSE: {diag.root_cause}
EVIDENCE: {diag.evidence}
CONFIDENCE: {diag.confidence}

Propose fixes."""

    try:
        raw = await complete_json(FIX_SYSTEM, user, config)
        items = raw if isinstance(raw, list) else raw.get("fixes", [])
    except Exception as e:
        # rail: store a single manual-investigation fix
        fix = SuggestedFix(
            diagnosis_id=diagnosis_id,
            fix_type="documentation",
            description=f"AI fix generation failed ({type(e).__name__}); inspect manually.",
            code=None,
            verification_test="",
        )
        db.add(fix)
        db.commit()
        return [fix]

    fixes = []
    for i, it in enumerate(items[:5]):
        fixes.append(SuggestedFix(
            diagnosis_id=diagnosis_id,
            fix_type=it.get("fix_type", "documentation"),
            description=str(it.get("description", "")),
            code=it.get("code"),
            verification_test=str(it.get("verification_test", "")),
        ))
    db.add_all(fixes)
    db.commit()
    return fixes
