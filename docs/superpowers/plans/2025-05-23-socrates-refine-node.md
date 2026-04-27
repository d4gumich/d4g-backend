# Task 6: Refine Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `refine_node` in the Socrates system to clarify user questions, identify assumptions, and missing information.

**Architecture:** A new LangGraph node `refine_node` will be created in `src/socrates/nodes/refine.py`. This node will use Gemini (Flash or Flash-Lite) to process user input based on the prompt provided. The node will be integrated into the `SocratesService` graph after the `classify` node.

**Tech Stack:** Python, FastAPI (backend), LangGraph (orchestration), Gemini (LLM), Pydantic (state management).

---

### Task 1: Create Refine Node

**Files:**
- Create: `src/socrates/nodes/refine.py`
- Test: `tests/test_socrates_refine.py`

- [ ] **Step 1: Write failing test for `refine_node`**

```python
import pytest
from src.socrates.schemas import SocratesState
from src.socrates.nodes.refine import refine_node
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_refine_node_success():
    state = SocratesState(
        raw_input="Should I quit my job?",
        session_id="test_session",
        run_id="test_run",
        selected_model="gemini-2.0-flash-lite"
    )

    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.text = '{"refined_question": "Under what conditions would quitting your job align with your long-term goals?", "assumptions": ["Quitting is an option", "You have long-term goals"], "missing_info": ["Current job satisfaction", "Financial situation"]}'

    with patch("google.generativeai.GenerativeModel.generate_content", return_value=mock_response):
        result = await refine_node(state)

    assert "refined_question" in result
    assert "assumptions" in result
    assert "missing_info" in result
    assert result["refined_question"] == "Under what conditions would quitting your job align with your long-term goals?"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_socrates_refine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.socrates.nodes.refine'`

- [ ] **Step 3: Implement `refine_node`**

```python
import json
import logging
import google.generativeai as genai
from src.core.settings import settings
from src.socrates.schemas import SocratesState

logger = logging.getLogger(__name__)

async def refine_node(state: SocratesState) -> dict:
    """
    Refines the user's input using Gemini.
    Returns a dictionary with refined_question, assumptions, and missing_info.
    """
    input_text = state.raw_input
    selected_model = state.selected_model

    prompt = f"""You are a master of Socratic refinement. Analyze the user's input and transform it into a stronger, clearer question. Identify hidden assumptions and missing information needed for a grounded answer.
Input: {input_text}

Return JSON with exactly these keys:
- refined_question: the stronger question
- assumptions: list of identified assumptions
- missing_info: list of information needed to move forward

Success criteria: A strong refine output should make the next reasoning step easier, narrower, and more honest."""

    # Configure API key
    genai.configure(api_key=settings.GOOGLE_API_KEY)

    # Use selected model
    model = genai.GenerativeModel(selected_model)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                candidate_count=1,
                max_output_tokens=1000,
                temperature=0.0,
                response_mime_type="application/json"
            ),
        )

        # Parse JSON response
        result = json.loads(response.text)

        logger.info(f"Refinement: refined_question={result.get('refined_question')}")

        return {
            "refined_question": result.get("refined_question"),
            "assumptions": result.get("assumptions", []),
            "missing_info": result.get("missing_info", []),
        }

    except Exception as e:
        logger.error(f"Error in refine_node: {e}")
        return {
            "refined_question": input_text,
            "assumptions": [],
            "missing_info": [],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_socrates_refine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/socrates/nodes/refine.py tests/test_socrates_refine.py
git commit -m "feat(socrates): add refinement node"
```

---

### Task 2: Update Socrates Service

**Files:**
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Write failing test for Service integration**

```python
import pytest
from src.socrates.service import SocratesService

def test_service_graph_registration():
    service = SocratesService()
    # Check if 'refine' node exists in the graph
    assert "refine" in service.builder.nodes
    # Check if there is an edge from 'classify' to 'refine'
    # In LangGraph 0.2+, edges are in service.builder.edges
    # This check might vary based on LangGraph version
    # For now, we'll check if it compiles correctly
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_socrates_service_integration.py -v`
Expected: FAIL

- [ ] **Step 3: Register `refine_node` and add edge**

```python
# src/socrates/service.py

from src.socrates.nodes.refine import refine_node

# ... in _setup_graph
self.builder.add_node("refine", refine_node)
self.builder.add_edge("classify", "refine")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_socrates_service_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/socrates/service.py
git commit -m "feat(socrates): register refine node in service graph"
```
