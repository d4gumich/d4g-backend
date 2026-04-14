from typing import Literal

from pydantic import BaseModel, Field


class SocratesState(BaseModel):
    raw_input: str
    session_id: str
    run_id: str
    channel: str = "chat"
    mode: Literal["refine", "message", "decision", "analysis"] | None = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    route: Literal["light", "standard", "full"] | None = None
    selected_model: str = "gemini-2.0-flash"
    refined_question: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    thesis: str | None = None
    antithesis: str | None = None
    synthesis: str | None = None
    open_tensions: list[str] = Field(default_factory=list)
    next_action: str | None = None
    action_draft: str | None = None
    evaluator_scores: dict[str, int] = Field(default_factory=dict)
    passed_eval: bool = False
    retry_count: int = 0
    is_paused: bool = False
    self_correction_notes: str | None = None


class SocratesRequest(BaseModel):
    input: str
    session_id: str | None = None
    channel: str = "chat"


class SocratesResponse(BaseModel):
    run_id: str
    artifact_id: str | None = None
    output: str | None = None
