# Socrates State & Schemas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the state and schema definitions for the Socrates module.

**Architecture:** Use Pydantic to define the API request/response schemas and the internal `SocratesState`.

**Tech Stack:** Pydantic (Python)

---

### Task 1: Create Socrates Schemas

**Files:**
- Create: `src/socrates/schemas.py`
- Test: `tests/test_socrates_schemas.py`

- [ ] **Step 1: Write schemas to `src/socrates/schemas.py`**

```python
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SocratesState(BaseModel):
    raw_input: str
    session_id: str
    run_id: str
    channel: str = "chat"
    mode: Optional[Literal["refine", "message", "decision", "analysis"]] = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    route: Optional[Literal["light", "standard", "full"]] = None
    selected_model: str = "gemini-2.0-flash"
    refined_question: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    thesis: Optional[str] = None
    antithesis: Optional[str] = None
    synthesis: Optional[str] = None
    action_draft: Optional[str] = None
    evaluator_scores: Dict[str, int] = Field(default_factory=dict)
    passed_eval: bool = False
    retry_count: int = 0
    is_paused: bool = False


class SocratesRequest(BaseModel):
    input: str
    session_id: Optional[str] = None
    channel: str = "chat"


class SocratesResponse(BaseModel):
    run_id: str
    artifact_id: Optional[str] = None
    output: Optional[str] = None
```

- [ ] **Step 2: Create a simple test to verify schemas can be instantiated**

```python
from src.socrates.schemas import SocratesState, SocratesRequest, SocratesResponse

def test_socrates_request():
    req = SocratesRequest(input="What is life?", session_id="test_session")
    assert req.input == "What is life?"
    assert req.session_id == "test_session"
    assert req.channel == "chat"

def test_socrates_state():
    state = SocratesState(
        raw_input="What is life?",
        session_id="test_session",
        run_id="test_run"
    )
    assert state.raw_input == "What is life?"
    assert state.risk_level == "medium"
    assert state.selected_model == "gemini-2.0-flash"
    assert state.assumptions == []
```

- [ ] **Step 3: Run the tests**

Run: `pytest tests/test_socrates_schemas.py`
Expected: PASS

- [ ] **Step 4: Commit the changes**

Run: `git add src/socrates/schemas.py tests/test_socrates_schemas.py`
Run: `git commit -m "feat(socrates): add state and request/response schemas"`
