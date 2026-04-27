# Socrates v2 - Structured Inquiry Engine Architecture

**Date:** 2026-04-13
**Status:** Draft (Awaiting Review)
**Author:** Gemini CLI

---

## 1. Purpose
Socrates is a structured inquiry system designed to move users from vague, reactive thinking toward refined questions, explicit tensions, and grounded next actions. Version 2 integrates this logic as a first-class module within the existing FastAPI backend, utilizing LangGraph for orchestration and the Gemini API for agentic reasoning.

## 2. Design Principles
- **Small Deterministic Spine:** Use LangGraph to define an explicit, inspectable state machine.
- **Agentic Node Logic:** Employ Gemini's reasoning within defined nodes, not for unconstrained flow.
- **Adaptive Precision:** Route between Flash-Lite, Flash, and Pro models based on task complexity and risk.
- **Structured Memory:** Prioritize distilled "Dialectic Artifacts" over raw transcript hoarding.
- **Isolated Persistence:** Use a dedicated database instance for Socrates state and artifacts.

## 3. Architecture

### 3.1 Module Structure (`src/socrates/`)
Following the project's established modular pattern:
- `router.py`: API endpoints (`POST /run`, `GET /stream/{run_id}`, `POST /resume/{run_id}`).
- `service.py`: `SocratesService` containing the LangGraph `StateGraph` and persistence logic.
- `schemas.py`: Pydantic models for `SocratesState` and API payloads.
- `nodes/`: Individual logic for complex reasoning steps.
  - `classify.py`, `refine.py`, `dialectic.py`, `evaluator.py`, `action_draft.py`.

### 3.2 Orchestration: LangGraph
A `StateGraph` will manage the flow of the `SocratesState`.
- **Checkpointer:** `PostgresSaver` will be used to store serialized graph state at every node, enabling "Pause and Resume."
- **Streaming:** Utilize LangGraph's `.stream()` with Server-Sent Events (SSE) for real-time "thinking" feedback.

### 3.3 LLM Strategy: Adaptive Model Routing
The `CLASSIFY` node determines the model profile:
- **Light (Low Risk):** Gemini 2.0 Flash-Lite (Speed/Cost).
- **Standard (Medium Risk):** Gemini 2.0 Flash (Balanced Reasoning).
- **Full (High Risk):** Gemini 2.0 Pro (Deep Reasoning/Full Dialectic).
- **Auto-Upgrade:** The `EVALUATOR` can trigger a retry on a more capable model if lower-tier reasoning fails the rubric.

## 4. Data Models

### 4.1 `SocratesState` (Pydantic)
```python
class SocratesState(BaseModel):
    raw_input: str
    session_id: str
    run_id: str
    mode: Optional[Literal["refine", "message", "decision", "analysis"]]
    risk_level: Literal["low", "medium", "high"]
    route: Literal["light", "standard", "full"]
    selected_model: str
    refined_question: Optional[str]
    assumptions: List[str]
    missing_info: List[str]
    thesis: Optional[str]
    antithesis: Optional[str]
    synthesis: Optional[str]
    action_draft: Optional[str]
    evaluator_scores: Dict[str, int]
    passed_eval: bool
    retry_count: int
    is_paused: bool
```

### 4.2 Database Schema (Isolated Postgres)
- `sessions`: Tracks global user context.
- `runs`: Tracks individual reasoning cycles and metadata.
- `artifacts`: Stores the final structured synthesis.
- `evaluations`: Stores rubric-based scoring data.
- `checkpoints`: (Managed by LangGraph) Stores graph state for pause/resume.

## 5. Logic Flow & Adaptive Evaluation

### 5.1 The "Adaptive Mix" Loop
1. **Light Path:** Fully Automatic. `INTAKE` → `CLASSIFY` → `ACTION_DRAFT` → `RETURN`.
2. **Standard/Full Path:** Adaptive Hybrid.
   - Run `EVALUATOR`.
   - If `score < Threshold` AND `retry_count < 1`: **Auto-Retry** with "Self-Correction."
   - If `score < Threshold` AND `retry_count >= 1`: **Interrupt/Pause**.
   - Stream `event: interrupt` with rubric notes.
   - Wait for `POST /resume` (User Choice: "Try Again" or "Continue Anyway").

### 5.2 Node Definitions
- **INTAKE:** Normalize input into standard request.
- **CLASSIFY:** Determine mode, risk, route, and model profile.
- **REFINE:** Identify assumptions and missing info; strengthen the question.
- **THESIS/ANTITHESIS:** Construct the case and the counter-case.
- **SYNTHESIS:** Grounded conclusion from surviving logic.
- **EVALUATOR:** 0-2 score on Clarity, Assumptions, Missing Info, Epistemic Hygiene, Actionability.

## 6. Implementation & Deployment

### 6.1 Requirements (`pyproject.toml`)
- `langgraph`
- `langgraph-checkpoint-postgres`
- `psycopg2-binary` (existing)
- `google-generativeai` (existing)

### 6.2 PythonAnywhere Optimization
- **SSE Heartbeat:** 15-second keep-alive pings to prevent load balancer timeouts.
- **Async Tasks:** Use non-blocking background tasks for long-running reasoning cycles.
- **Isolated DB URL:** Separate environment variable `SOCRATES_DB_URL`.

## 7. Acceptance Criteria
- Classify 4 request types with >90% accuracy.
- Successfully stream "thinking" states via SSE.
- Correctly persist and resume a "Paused" graph state.
- Score outputs against a rubric and trigger auto-retry/interrupt logic.
- Store results as structured artifacts in the isolated database.
