"""
Growth Engine endpoints — experiment management, playbook, scorecards.
"""
import os
import sys
import json
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter()

_SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "marketing-skills", "growth-engine",
)
DATA_DIR = os.environ.get("GROWTH_ENGINE_DATA_DIR", os.path.join(_SKILLS_DIR, "data", "experiments"))


class CreateExperimentRequest(BaseModel):
    agent: str = "content"
    hypothesis: str = ""
    variable: str = ""
    variants: list[str] = []
    metric: str = "conversions"
    cycle_hours: int = 24
    batch_mode: bool = False
    min_samples: Optional[int] = None


class LogDataRequest(BaseModel):
    experiment_id: str
    variant: str
    metrics: dict


def _import_skill(name: str):
    if _SKILLS_DIR not in sys.path:
        sys.path.insert(0, _SKILLS_DIR)
    return __import__(name)


@router.get("/config")
def growth_config():
    """Return growth engine configuration."""
    return {
        "data_dir": DATA_DIR,
        "agents": os.environ.get("GROWTH_ENGINE_AGENTS", "content,email,linkedin,seo,blog"),
        "high_volume_agents": os.environ.get("HIGH_VOLUME_AGENTS", "content,email"),
        "low_volume_agents": os.environ.get("LOW_VOLUME_AGENTS", "seo,linkedin,blog"),
        "p_winner": float(os.environ.get("P_WINNER", "0.05")),
        "p_trend": float(os.environ.get("P_TREND", "0.10")),
        "lift_win": float(os.environ.get("LIFT_WIN", "15.0")),
    }


@router.post("/experiments/create")
def create_experiment(req: CreateExperimentRequest):
    """Create a new growth experiment."""
    try:
        mod = _import_skill("experiment-engine")
        result = mod.create_experiment(
            agent=req.agent,
            hypothesis=req.hypothesis,
            variable=req.variable,
            variants=req.variants,
            metric=req.metric,
            cycle_hours=req.cycle_hours,
            batch_mode=req.batch_mode,
            min_samples=req.min_samples,
        )
        return {"success": True, "experiment": result}
    except ImportError:
        # Fallback: create experiment JSON manually
        from datetime import datetime, timezone
        exp_id = f"EXP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        experiment = {
            "id": exp_id,
            "agent": req.agent,
            "hypothesis": req.hypothesis,
            "variable": req.variable,
            "variants": req.variants,
            "metric": req.metric,
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(os.path.join(DATA_DIR, f"{exp_id}.json"), "w") as f:
            json.dump(experiment, f, indent=2)
        return {"success": True, "experiment": experiment, "note": "Created via fallback (experiment-engine not importable)"}
    except Exception as e:
        raise HTTPException(500, f"Create experiment error: {str(e)}")


@router.post("/experiments/log")
def log_experiment_data(req: LogDataRequest):
    """Log a data point for a running experiment."""
    try:
        mod = _import_skill("experiment-engine")
        result = mod.log_data(
            experiment_id=req.experiment_id,
            variant=req.variant,
            metrics=req.metrics,
        )
        return {"success": True, "result": result}
    except ImportError:
        return {"success": False, "error": "experiment-engine not importable"}
    except Exception as e:
        raise HTTPException(500, f"Log data error: {str(e)}")


@router.get("/experiments")
def list_experiments(
    agent: Optional[str] = None,
    status: Optional[str] = None,
):
    """List experiments, optionally filtered by agent and status."""
    experiments = []
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, f)) as fh:
                        exp = json.load(fh)
                    if agent and exp.get("agent") != agent:
                        continue
                    if status and exp.get("status") != status:
                        continue
                    experiments.append(exp)
                except Exception:
                    pass
    return {"success": True, "experiments": experiments}


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    """Get a single experiment by ID."""
    path = os.path.join(DATA_DIR, f"{experiment_id}.json")
    if not os.path.exists(path):
        raise HTTPException(404, "Experiment not found")
    with open(path) as f:
        return {"success": True, "experiment": json.load(f)}


@router.post("/experiments/{experiment_id}/score")
def score_experiment(experiment_id: str):
    """Score an experiment and auto-promote winner if criteria met."""
    try:
        mod = _import_skill("experiment-engine")
        result = mod.score_experiment(experiment_id=experiment_id)
        return {"success": True, "result": result}
    except ImportError:
        return {"success": False, "error": "experiment-engine not importable"}
    except Exception as e:
        raise HTTPException(500, f"Score error: {str(e)}")


@router.get("/playbook")
def get_playbook(agent: Optional[str] = None):
    """Get the living playbook of proven best practices."""
    playbook_path = os.path.join(DATA_DIR, "playbook.json")
    if os.path.exists(playbook_path):
        with open(playbook_path) as f:
            playbook = json.load(f)
        if agent:
            playbook = {k: v for k, v in playbook.items() if k == agent}
        return {"success": True, "playbook": playbook}
    return {"success": True, "playbook": {}, "message": "No playbook entries yet. Run experiments to build it."}


@router.get("/scorecard")
def get_scorecard(weeks: int = Query(4, ge=1, le=52)):
    """Generate a weekly scorecard across all channels."""
    try:
        mod = _import_skill("autogrowth-weekly-scorecard")
        result = mod.generate_scorecard(weeks=weeks)
        return {"success": True, "scorecard": result}
    except ImportError:
        return {"success": False, "error": "autogrowth-weekly-scorecard not importable"}
    except Exception as e:
        raise HTTPException(500, f"Scorecard error: {str(e)}")
