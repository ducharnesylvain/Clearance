"""Run one request through one architecture and one model, and validate the answer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from .models import Completion, Model
from .pack import Pack
from .prompts import system_prompt, user_prompt
from .schema import Decision

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class EngineResult:
    decision: Decision | None
    error: str | None
    raw_text: str
    completion: Completion


def extract_json(text: str) -> dict:
    """Parse the first JSON object in a model answer, tolerating code fences and prose around it."""
    cleaned = _FENCE.sub("", text.strip())
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("no JSON object in the answer")
    obj, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    if not isinstance(obj, dict):
        raise ValueError("the answer is not a JSON object")
    return obj


def run(pack: Pack, model: Model, arch: str, request: str, context: str = "") -> EngineResult:
    completion = model.complete(system_prompt(pack), user_prompt(arch, pack, request, context))
    try:
        decision = Decision.model_validate(extract_json(completion.text))
        return EngineResult(decision, None, completion.text, completion)
    except (ValueError, ValidationError) as exc:
        message = str(exc).splitlines()[0][:300]
        return EngineResult(None, f"invalid output: {message}", completion.text, completion)
