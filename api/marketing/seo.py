"""
SEO Ops endpoints — keyword intelligence, GSC optimization, trend scouting.
"""
import os
import sys
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
AHREFS_TOKEN = os.getenv("AHREFS_TOKEN", "")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "")
COMPETITORS = [c.strip() for c in os.getenv("COMPETITORS", "").split(",") if c.strip()]
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "")

_SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "marketing-skills", "seo-ops",
)


def _import_skill(name: str):
    """Import a module from the seo-ops skill directory."""
    if _SKILLS_DIR not in sys.path:
        sys.path.insert(0, _SKILLS_DIR)
    return __import__(name)


@router.get("/config")
def seo_config():
    """Return which SEO features are configured."""
    return {
        "gsc_configured": bool(GSC_SITE_URL and GOOGLE_CLIENT_ID),
        "ahrefs_configured": bool(AHREFS_TOKEN),
        "brave_configured": bool(BRAVE_API_KEY),
        "domain": YOUR_DOMAIN,
        "competitors": COMPETITORS,
    }


@router.get("/trends")
def get_trends(
    vertical: Optional[str] = Query(None, description="Content vertical to filter trends"),
    limit: int = Query(20, ge=1, le=100),
):
    """Fetch trending topics from Google Trends, HN, Reddit."""
    try:
        mod = _import_skill("trend_scout")
        results = mod.scout_trends(vertical=vertical, limit=limit)
        return {"success": True, "data": results}
    except ImportError:
        return {"success": False, "error": "trend_scout module not available"}
    except Exception as e:
        raise HTTPException(500, f"Trend scout error: {str(e)}")


@router.get("/gsc/striking-distance")
def striking_distance(
    days: int = Query(28, ge=1, le=90),
    min_pos: int = Query(4, ge=1, le=20),
    max_pos: int = Query(20, ge=1, le=50),
    limit: int = Query(50, ge=1, le=200),
):
    """Find striking-distance keywords (positions 4-20 with good impressions)."""
    if not GSC_SITE_URL or not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "GSC not configured. Set GSC_SITE_URL and GOOGLE_CLIENT_ID.")
    try:
        mod = _import_skill("gsc_client")
        gsc = mod.GSCClient()
        rows = gsc.striking_distance(days=days, min_position=min_pos, max_position=max_pos)
        return {
            "success": True,
            "data": [
                {
                    "keyword": row["keys"][0] if row.get("keys") else "",
                    "position": row.get("position", 0),
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "ctr": row.get("ctr", 0),
                }
                for row in rows[:limit]
            ],
        }
    except Exception as e:
        raise HTTPException(500, f"GSC error: {str(e)}")


@router.get("/gsc/queries")
def gsc_queries(
    days: int = Query(28, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
):
    """Fetch top GSC queries."""
    if not GSC_SITE_URL or not GOOGLE_CLIENT_ID:
        raise HTTPException(503, "GSC not configured.")
    try:
        mod = _import_skill("gsc_client")
        gsc = mod.GSCClient()
        rows = gsc.top_queries(days=days, limit=limit)
        return {
            "success": True,
            "data": [
                {
                    "query": row.get("keys", [""])[0] if row.get("keys") else "",
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "position": row.get("position", 0),
                    "ctr": row.get("ctr", 0),
                }
                for row in rows
            ],
        }
    except Exception as e:
        raise HTTPException(500, f"GSC error: {str(e)}")


@router.get("/competitor-gaps")
def competitor_gaps():
    """Find keywords competitors rank for that we don't."""
    if not AHREFS_TOKEN:
        raise HTTPException(503, "Ahrefs not configured. Set AHREFS_TOKEN.")
    if not COMPETITORS:
        raise HTTPException(503, "No competitors configured. Set COMPETITORS.")
    try:
        mod = _import_skill("content_attack_brief")
        gaps = mod.find_competitor_gaps(domain=YOUR_DOMAIN, competitors=COMPETITORS, ahrefs_token=AHREFS_TOKEN)
        return {"success": True, "data": gaps}
    except ImportError:
        return {"success": False, "error": "content_attack_brief module not available"}
    except Exception as e:
        raise HTTPException(500, f"Competitor gap error: {str(e)}")
