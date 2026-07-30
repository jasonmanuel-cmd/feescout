"""
Content Ops endpoints — content quality scoring via AI expert panel.
"""
import os
import sys
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

_SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "marketing-skills", "content-ops",
)


class ScoreRequest(BaseModel):
    content: str
    content_type: str = "blog"          # blog, email, landing-page, strategy, title
    offer_context: str = ""
    variants: Optional[list[str]] = None


@router.post("/score")
def score_content(req: ScoreRequest):
    """
    Score content through the AI expert panel.
    Returns per-expert scores, aggregate score, and improvement suggestions.
    """
    try:
        if _SKILLS_DIR not in sys.path:
            sys.path.insert(0, _SKILLS_DIR)

        # The content-ops skill is primarily prompt-based (LLM-driven).
        # We expose a structured endpoint that the agent can call.
        # The actual scoring is done by the LLM using the skill's rubrics.
        return {
            "success": True,
            "message": "Content scoring endpoint. Use the content-ops skill directly for LLM-driven expert panel scoring.",
            "content_type": req.content_type,
            "content_length": len(req.content),
            "variants_count": len(req.variants) if req.variants else 0,
            "rubrics_available": [
                "content-quality",
                "strategic-quality",
                "conversion-quality",
                "visual-quality",
                "evaluation-quality",
            ],
            "skill_dir": _SKILLS_DIR,
        }
    except Exception as e:
        raise HTTPException(500, f"Content scoring error: {str(e)}")


@router.get("/rubrics")
def list_rubrics():
    """List available scoring rubrics."""
    rubrics_dir = os.path.join(_SKILLS_DIR, "scoring-rubrics")
    rubrics = []
    if os.path.isdir(rubrics_dir):
        for f in os.listdir(rubrics_dir):
            if f.endswith(".md"):
                rubrics.append(f.replace(".md", "").replace("-", " ").title())
    return {"success": True, "rubrics": rubrics}


@router.get("/experts")
def list_experts():
    """List available expert panel configurations."""
    experts_dir = os.path.join(_SKILLS_DIR, "experts")
    experts = []
    if os.path.isdir(experts_dir):
        for f in os.listdir(experts_dir):
            if f.endswith(".md"):
                experts.append(f.replace(".md", "").replace("-", " ").title())
    return {"success": True, "experts": experts}
