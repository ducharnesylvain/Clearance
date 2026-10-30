"""Thin adapters over the official vendor SDKs, plus a fake model for tests.

Models are configured in evals/models.yaml. API keys come from environment
variables only: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY.
SDKs are imported lazily so the package and its tests run without them.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import yaml


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float


class Model(Protocol):
    name: str
    model_id: str

    def complete(self, system: str, user: str) -> Completion: ...


@dataclass
class ModelSpec:
    name: str
    provider: str
    model_id: str | None
    max_tokens: int = 2000
    temperature: float | None = 0.0
    price_in_per_mtok: float | None = None
    price_out_per_mtok: float | None = None

    def cost(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.price_in_per_mtok is None or self.price_out_per_mtok is None:
            return None
        return (input_tokens * self.price_in_per_mtok + output_tokens * self.price_out_per_mtok) / 1_000_000


def load_specs(path: str | Path = "evals/models.yaml") -> dict[str, ModelSpec]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {name: ModelSpec(name=name, **cfg) for name, cfg in data["models"].items()}


def _require_key(var: str) -> str:
    key = os.environ.get(var)
    if not key:
        raise RuntimeError(f"{var} is not set. Add it as an environment variable or a GitHub secret.")
    return key


class AnthropicModel:
    def __init__(self, spec: ModelSpec):
        import anthropic

        self.name, self.model_id, self.spec = spec.name, spec.model_id, spec
        self.client = anthropic.Anthropic(api_key=_require_key("ANTHROPIC_API_KEY"))

    def complete(self, system: str, user: str) -> Completion:
        kwargs = {"model": self.model_id, "max_tokens": self.spec.max_tokens, "system": system,
                  "messages": [{"role": "user", "content": user}]}
        if self.spec.temperature is not None:
            kwargs["temperature"] = self.spec.temperature
        t0 = time.perf_counter()
        resp = self.client.messages.create(**kwargs)
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        return Completion(text, resp.usage.input_tokens, resp.usage.output_tokens, time.perf_counter() - t0)


class OpenAIModel:
    def __init__(self, spec: ModelSpec):
        import openai

        self.name, self.model_id, self.spec = spec.name, spec.model_id, spec
        self.client = openai.OpenAI(api_key=_require_key("OPENAI_API_KEY"))

    def complete(self, system: str, user: str) -> Completion:
        kwargs = {"model": self.model_id, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if self.spec.temperature is not None:
            kwargs["temperature"] = self.spec.temperature
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(**kwargs)
        usage = resp.usage
        return Completion(resp.choices[0].message.content or "", usage.prompt_tokens,
                          usage.completion_tokens, time.perf_counter() - t0)


class GoogleModel:
    def __init__(self, spec: ModelSpec):
        from google import genai

        self.name, self.model_id, self.spec = spec.name, spec.model_id, spec
        self.client = genai.Client(api_key=_require_key("GOOGLE_API_KEY"))

    def complete(self, system: str, user: str) -> Completion:
        from google.genai import types

        config = types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json",
                                             max_output_tokens=self.spec.max_tokens)
        if self.spec.temperature is not None:
            config.temperature = self.spec.temperature
        t0 = time.perf_counter()
        resp = self.client.models.generate_content(model=self.model_id, contents=user, config=config)
        meta = resp.usage_metadata
        return Completion(resp.text or "", meta.prompt_token_count or 0, meta.candidates_token_count or 0,
                          time.perf_counter() - t0)


class FakeModel:
    """Deterministic stand-in for tests and offline dry runs."""

    def __init__(self, responder: Callable[[str, str], str], name: str = "fake"):
        self.name = self.model_id = name
        self.responder = responder

    def complete(self, system: str, user: str) -> Completion:
        text = self.responder(system, user)
        return Completion(text, len(system + user) // 4, len(text) // 4, 0.0)


PROVIDERS = {"anthropic": AnthropicModel, "openai": OpenAIModel, "google": GoogleModel}


def build_model(spec: ModelSpec) -> Model:
    if not spec.model_id:
        raise RuntimeError(f"Model '{spec.name}' has no model_id yet. Pin it in evals/models.yaml before running.")
    return PROVIDERS[spec.provider](spec)
