"""The decision contract (SPEC section 5). Every answer is validated against it."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

Verdict = Literal["clear", "clear_with_conditions", "blocked", "escalate"]
EscalationReason = Literal["missing_rule", "conflicting_rules", "out_of_scope", "low_confidence"]


class Claim(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)


class Risk(Claim):
    severity: Literal["low", "medium", "high"]


class Question(BaseModel):
    text: str


class Citation(BaseModel):
    id: str
    doc_id: str
    version: str
    section: str
    quote: str

    @field_validator("version", "section", mode="before")
    @classmethod
    def _as_text(cls, value: object) -> str:
        # Models sometimes emit 3.0 or 4.2 as numbers.
        return value if isinstance(value, str) else str(value)


class Decision(BaseModel):
    verdict: Verdict
    summary: str
    conditions: list[Claim] = Field(default_factory=list)
    required_actions: list[Claim] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    open_questions: list[Question] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    escalation_reason: Optional[EscalationReason] = None

    @model_validator(mode="after")
    def _reason_matches_verdict(self) -> "Decision":
        if self.verdict == "escalate" and self.escalation_reason is None:
            raise ValueError("an escalation needs an escalation_reason")
        if self.verdict != "escalate" and self.escalation_reason is not None:
            raise ValueError("escalation_reason is only allowed when verdict is escalate")
        return self

    def claims(self) -> list[Claim]:
        """Everything that asserts something and therefore needs a source."""
        return [*self.conditions, *self.required_actions, *self.risks]
