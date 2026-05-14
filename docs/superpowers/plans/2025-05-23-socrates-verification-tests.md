# Socrates Branching Logic & Integration Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement branching logic in the Socrates service to route requests based on risk level and complete integration tests for all paths.

**Architecture:** Use LangGraph's `add_conditional_edges` to route from the `classify` node to either `refine` (Standard/Full paths) or `action_draft` (Light path).

**Tech Stack:** Python, FastAPI, LangGraph, Pytest

---

### Task 1: Update Socrates Service Branching Logic

**Files:**
- Modify: `src/socrates/service.py`

- [ ] **Step 1: Define the routing function for the `classify` node**

```python
def route_after_classify(state: SocratesState) -> str:
    """Routes based on risk level from classification."""
    if state.route == "light":
        logger.info("Low risk detected. Routing to Light path (action_draft).")
        return "action_draft"
    logger.info(f"{state.route.capitalize()} path selected. Routing to refine.")
    return "refine"
```

- [ ] **Step 2: Update `_setup_graph` to use conditional edges from `classify`**

```python
    def _setup_graph(self):
        """Adds nodes and edges to the LangGraph builder."""
        self.builder.add_node("classify", classify_node)
        self.builder.add_node("refine", refine_node)
        self.builder.add_node("thesis", thesis_node)
        self.builder.add_node("antithesis", antithesis_node)
        self.builder.add_node("synthesis", synthesis_node)
        self.builder.add_node("action_draft", action_draft_node)
        self.builder.add_node("evaluator", evaluator_node)

        self.builder.set_entry_point("classify")

        # Branching logic from classify
        self.builder.add_conditional_edges(
            "classify",
            route_after_classify,
            {"refine": "refine", "action_draft": "action_draft"},
        )

        self.builder.add_edge("refine", "thesis")
        self.builder.add_edge("thesis", "antithesis")
        self.builder.add_edge("antithesis", "synthesis")
        self.builder.add_edge("synthesis", "action_draft")
        self.builder.add_edge("action_draft", "evaluator")

        self.builder.add_conditional_edges(
            "evaluator",
            route_after_eval,
            {"synthesis": "synthesis", END: END},
        )
```

- [ ] **Step 3: Commit changes**

```bash
git add src/socrates/service.py
git commit -m "feat(socrates): implement branching logic in service"
```

### Task 2: Implement Standard Path Integration Test

**Files:**
- Modify: `tests/test_socrates.py`

- [ ] **Step 1: Add `test_socrates_standard_path`**

```python
@pytest.mark.asyncio
async def test_socrates_standard_path(mock_gemini):
    """
    Tests the 'standard' path: CLASSIFY -> REFINE -> THESIS -> ANTITHESIS -> SYNTHESIS -> ACTION_DRAFT -> EVALUATOR -> END.
    Standard path visits all nodes.
    """
    def side_effect(prompt, **kwargs):
        mock_response = MagicMock()
        if "master of classification" in prompt:
            mock_response.text = json.dumps({
                "mode": "refine",
                "risk_level": "moderate",
                "route": "standard"
            })
        elif "refine" in prompt:
            mock_response.text = json.dumps({"refined_input": "Moderate risk input"})
        elif "thesis" in prompt:
            mock_response.text = json.dumps({"thesis": "Thesis for moderate risk"})
        elif "antithesis" in prompt:
            mock_response.text = json.dumps({"antithesis": "Antithesis for moderate risk"})
        elif "synthesis" in prompt:
            mock_response.text = json.dumps({"synthesis": "Synthesis for moderate risk"})
        elif "master of Socratic communication" in prompt:
            mock_response.text = json.dumps({"action_draft": "Action draft for moderate risk"})
        elif "evaluator" in prompt:
            mock_response.text = json.dumps({"score": 0.9, "feedback": "Pass", "passed": True})
        else:
            mock_response.text = json.dumps({"error": f"Unexpected node call: {prompt[:50]}"})
        return mock_response

    mock_gemini.side_effect = side_effect

    response = client.post(
        "/api/v1/socrates/run",
        json={"input": "Moderate risk query", "session_id": "test_standard"}
    )

    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            events.append(json.loads(line[6:].decode()))

    node_names = [list(event.keys())[0] for event in events]
    
    assert "classify" in node_names
    assert "refine" in node_names
    assert "thesis" in node_names
    assert "antithesis" in node_names
    assert "synthesis" in node_names
    assert "action_draft" in node_names
    assert "evaluator" in node_names
```

### Task 3: Implement Full Path Integration Test

**Files:**
- Modify: `tests/test_socrates.py`

- [ ] **Step 1: Add `test_socrates_full_path`**

```python
@pytest.mark.asyncio
async def test_socrates_full_path(mock_gemini):
    """
    Tests the 'full' path: CLASSIFY -> REFINE -> THESIS -> ANTITHESIS -> SYNTHESIS -> ACTION_DRAFT -> EVALUATOR -> END.
    Full path also visits all nodes (like standard, but with higher risk).
    """
    def side_effect(prompt, **kwargs):
        mock_response = MagicMock()
        if "master of classification" in prompt:
            mock_response.text = json.dumps({
                "mode": "refine",
                "risk_level": "high",
                "route": "full"
            })
        elif "refine" in prompt:
            mock_response.text = json.dumps({"refined_input": "High risk input"})
        elif "thesis" in prompt:
            mock_response.text = json.dumps({"thesis": "Thesis for high risk"})
        elif "antithesis" in prompt:
            mock_response.text = json.dumps({"antithesis": "Antithesis for high risk"})
        elif "synthesis" in prompt:
            mock_response.text = json.dumps({"synthesis": "Synthesis for high risk"})
        elif "master of Socratic communication" in prompt:
            mock_response.text = json.dumps({"action_draft": "Action draft for high risk"})
        elif "evaluator" in prompt:
            mock_response.text = json.dumps({"score": 0.95, "feedback": "Pass", "passed": True})
        else:
            mock_response.text = json.dumps({"error": f"Unexpected node call: {prompt[:50]}"})
        return mock_response

    mock_gemini.side_effect = side_effect

    response = client.post(
        "/api/v1/socrates/run",
        json={"input": "High risk query", "session_id": "test_full"}
    )

    assert response.status_code == 200
    
    events = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            events.append(json.loads(line[6:].decode()))

    node_names = [list(event.keys())[0] for event in events]
    
    assert "classify" in node_names
    assert "refine" in node_names
    assert "thesis" in node_names
    assert "antithesis" in node_names
    assert "synthesis" in node_names
    assert "action_draft" in node_names
    assert "evaluator" in node_names
```

### Task 4: Run Verification Tests

**Files:**
- Run: `uv run pytest tests/test_socrates.py`

- [ ] **Step 1: Verify all paths pass and transition as expected**

Run: `uv run pytest tests/test_socrates.py -v`
Expected: 3 tests pass (light, standard, full)

- [ ] **Step 2: Commit final changes**

```bash
git add tests/test_socrates.py
git commit -m "test(socrates): add integration tests for full reasoning graph"
```
