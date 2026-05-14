# Socrates v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a structured inquiry system (Socrates) integrated into the FastAPI backend using LangGraph and Gemini.

**Architecture:** A stateful LangGraph workflow with adaptive model routing (Flash-Lite to Pro) and an isolated PostgreSQL database for persistence and "Pause and Resume" capabilities.

**Tech Stack:** Python, FastAPI, LangGraph, `langgraph-checkpoint-postgres`, `google-generativeai`.

---

### Task 1: Environment & Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`
- Modify: `src/core/settings.py`

- [ ] **Step 1: Add new dependencies to `pyproject.toml`**

```toml
dependencies = [
    # ... existing
    "langgraph>=0.0.15",
    "langgraph-checkpoint-postgres>=1.0.0",
]
```

- [ ] **Step 2: Update `.env.example` with Socrates database variables**

```bash
# Socrates DB
SOCRATES_DB_URL=postgresql://user:pass@host:port/socrates_db
```

- [ ] **Step 3: Update `src/core/settings.py` to include Socrates settings**

```python
class Settings(BaseSettings):
    # ...
    SOCRATES_DB_URL: str | None = None
    SOCRATES_DEEP_MODEL: str = "gemini-2.0-pro"
    SOCRATES_STANDARD_MODEL: str = "gemini-2.0-flash"
    SOCRATES_LIGHT_MODEL: str = "gemini-2.0-flash-lite"
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .env.example src/core/settings.py
git commit -m "chore: add socrates dependencies and settings"
```

---

### Task 2: Socrates State & Schemas

**Files:**
- Create: `src/socrates/schemas.py`

- [ ] **Step 1: Define the `SocratesState` and API schemas**

```python
from typing import Optional, Literal, List, Dict, Any
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

- [ ] **Step 2: Commit**

```bash
git add src/socrates/schemas.py
git commit -m "feat(socrates): add state and request/response schemas"
```

---

### Task 3: Base Socrates Service & Graph Shell

**Files:**
- Create: `src/socrates/service.py`

- [ ] **Step 1: Implement the `SocratesService` with a shell LangGraph**

```python
import logging
from langgraph.graph import StateGraph, END
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)

class SocratesService:
    def __init__(self):
        self.builder = StateGraph(SocratesState)
        self._setup_graph()
        self.graph = self.builder.compile()

    def _setup_graph(self):
        # We will add nodes in subsequent tasks
        pass

    async def run(self, request_data: dict):
        # Entry point for the graph
        pass

socrates_service = SocratesService()
```

- [ ] **Step 2: Commit**

```bash
git add src/socrates/service.py
git commit -m "feat(socrates): initialize socrates service and graph shell"
```

---

### Task 4: Classifier Node

**Files:**
- Create: `src/socrates/nodes/classify.py`
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Create the `classify_node` with model routing**

```python
import google.generativeai as genai
from src.core.settings import settings
from src.socrates.schemas import SocratesState

async def classify_node(state: SocratesState) -> dict:
    prompt = f"Classify this request: {state.raw_input}. Return JSON with mode, risk_level, and route."
    # Use Gemini Flash-Lite for classification
    model = genai.GenerativeModel(settings.SOCRATES_LIGHT_MODEL)
    # ... logic to call Gemini and update state
    return {"mode": "decision", "risk_level": "medium", "route": "standard", "selected_model": settings.SOCRATES_STANDARD_MODEL}
```

- [ ] **Step 2: Register node in `SocratesService`**

```python
from src.socrates.nodes.classify import classify_node

# In _setup_graph:
self.builder.add_node("classify", classify_node)
self.builder.set_entry_point("classify")
```

- [ ] **Step 3: Commit**

```bash
git add src/socrates/nodes/classify.py src/socrates/service.py
git commit -m "feat(socrates): add classification node"
```

---

### Task 5: Refine Node

**Files:**
- Create: `src/socrates/nodes/refine.py`
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Create the `refine_node`**

```python
async def refine_node(state: SocratesState) -> dict:
    # Logic to identify assumptions and missing info
    return {"refined_question": "...", "assumptions": ["..."], "missing_info": ["..."]}
```

- [ ] **Step 2: Register node and edge in `SocratesService`**

```python
self.builder.add_node("refine", refine_node)
self.builder.add_edge("classify", "refine")
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(socrates): add refinement node"
```

---

### Task 6: Dialectic Nodes (Thesis, Antithesis, Synthesis)

**Files:**
- Create: `src/socrates/nodes/dialectic.py`
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Implement the dialectic nodes**

```python
async def thesis_node(state: SocratesState): ...
async def antithesis_node(state: SocratesState): ...
async def synthesis_node(state: SocratesState): ...
```

- [ ] **Step 2: Add nodes and edges to graph**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(socrates): add dialectic reasoning nodes"
```

---

### Task 7: Evaluator Node & Adaptive Mix Logic

**Files:**
- Create: `src/socrates/nodes/evaluator.py`
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Implement the `evaluator_node` with rubric scoring**

- [ ] **Step 2: Implement the "Adaptive Mix" conditional routing**

```python
def route_after_eval(state: SocratesState):
    if state.passed_eval:
        return "end"
    if state.retry_count < 1:
        return "retry"
    return "pause"
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(socrates): add evaluator and adaptive routing"
```

---

### Task 8: API Router & Streaming (SSE)

**Files:**
- Create: `src/socrates/router.py`
- Modify: `src/main.py`

- [ ] **Step 1: Implement the FastAPI router with SSE streaming**

```python
from fastapi.responses import StreamingResponse

@router.post("/run")
async def run_socrates(request: SocratesRequest):
    async def event_generator():
        async for event in socrates_service.graph.astream(initial_state):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: Register the router in `src/main.py`**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(socrates): add api router with streaming support"
```

---

### Task 9: Isolated Database Persistence

**Files:**
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Configure `PostgresSaver` in `SocratesService`**

```python
from langgraph.checkpoint.postgres import PostgresSaver

# In __init__:
self.checkpointer = PostgresSaver.from_conn_string(settings.SOCRATES_DB_URL)
self.graph = self.builder.compile(checkpointer=self.checkpointer)
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(socrates): add postgres persistence for graph state"
```

---

### Task 10: Verification & Tests

**Files:**
- Create: `tests/test_socrates.py`

- [ ] **Step 1: Write integration tests for the Socrates graph**

- [ ] **Step 2: Run tests and verify all nodes execute**

- [ ] **Step 3: Commit**

```bash
git commit -m "test(socrates): add integration tests"
```
