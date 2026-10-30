"""Clearance: an eval-first AI decision copilot for business rules."""

from __future__ import annotations

from pathlib import Path

from .engine import EngineResult, run
from .models import build_model, load_specs
from .pack import Pack, load_pack
from .schema import Decision

__all__ = ["Decision", "EngineResult", "Pack", "decide", "load_pack"]


def decide(pack: str | Path,  # pack folder, or a pack name under domains/
           request: str, context: str = "", model: str = "claude-small",
           arch: str = "B", models_file: str | Path = "evals/models.yaml") -> EngineResult:
    """Check one request against a domain pack. Needs the model's API key in the environment."""
    pack_path = Path(pack)
    if not pack_path.exists():
        pack_path = Path("domains") / str(pack)
    spec = load_specs(models_file)[model]
    return run(load_pack(pack_path), build_model(spec), arch, request, context)
