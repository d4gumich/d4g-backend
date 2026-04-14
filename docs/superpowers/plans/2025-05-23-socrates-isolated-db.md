# Socrates Isolated Database Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Task 10: Isolated Database Persistence for `SocratesService` using `PostgresSaver` from `langgraph-checkpoint-postgres`.

**Architecture:** Update `SocratesService` to use a `PostgresSaver` checkpointer for graph state persistence. This allows the graph state to be saved and resumed across different requests and application restarts.

**Tech Stack:** `langgraph`, `langgraph-checkpoint-postgres`, `psycopg`.

---

### Task 1: Update SocratesService with Postgres Persistence

**Files:**
- Modify: `src/socrates/service.py`
- Test: `tests/test_socrates_service_integration.py`

- [ ] **Step 1: Modify `src/socrates/service.py` to import `PostgresSaver` and initialize it**

```python
import logging

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph

from src.core.settings import settings
from src.socrates.nodes.action_draft import action_draft_node
# ... (rest of imports)

logger = logging.getLogger(__name__)

# ... (route_after_eval function)

class SocratesService:
    def __init__(self):
        self.builder = StateGraph(SocratesState)
        self._setup_graph()
        
        # Configure checkpointer if DB URL is provided
        if settings.SOCRATES_DB_URL:
            try:
                # Use PostgresSaver for persistence
                self.checkpointer = PostgresSaver.from_conn_string(settings.SOCRATES_DB_URL)
                # Ensure the checkpoints table is created
                # Note: setup() is usually called once or handled automatically
                self.checkpointer.setup()
                self.graph = self.builder.compile(checkpointer=self.checkpointer)
                logger.info("SocratesService: Postgres checkpointer initialized.")
            except Exception as e:
                logger.error(f"SocratesService: Failed to initialize Postgres checkpointer: {e}")
                # Fallback to no persistence if DB connection fails
                self.graph = self.builder.compile()
        else:
            logger.warning("SocratesService: SOCRATES_DB_URL not set. Persistence disabled.")
            self.graph = self.builder.compile()
```

- [ ] **Step 2: Update `tests/test_socrates_service_integration.py` to verify initialization logic**

```python
from unittest.mock import patch, MagicMock
from src.socrates.service import SocratesService
from src.core.settings import settings

def test_service_initialization_no_db():
    with patch.object(settings, 'SOCRATES_DB_URL', None):
        service = SocratesService()
        assert service.graph is not None
        # Verify it compiled without error

def test_service_initialization_with_db_error():
    with patch.object(settings, 'SOCRATES_DB_URL', 'postgresql://invalid:invalid@localhost:5432/invalid'):
        # Mock PostgresSaver.from_conn_string to raise an exception
        with patch('langgraph.checkpoint.postgres.PostgresSaver.from_conn_string') as mock_from_conn:
            mock_from_conn.side_effect = Exception("Connection refused")
            service = SocratesService()
            assert service.graph is not None
            # Should still compile without checkpointer
```

- [ ] **Step 3: Run existing tests to ensure no regressions**

Run: `pytest tests/test_socrates_service_integration.py -v`
Expected: PASS

- [ ] **Step 4: Commit the changes**

```bash
git add src/socrates/service.py tests/test_socrates_service_integration.py
git commit -m "feat(socrates): add postgres persistence for graph state"
```
