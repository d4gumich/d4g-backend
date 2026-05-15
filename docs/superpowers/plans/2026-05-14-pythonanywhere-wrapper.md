# PythonAnywhere Wrapper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a WSGI wrapper for the FastAPI backend using `a2wsgi` in `src/main.py` to support PythonAnywhere deployments.

**Architecture:** Use `a2wsgi.ASGIMiddleware` to wrap the FastAPI ASGI application into a WSGI-compliant application object.

**Tech Stack:** Python, FastAPI, a2wsgi.

---

### Task 1: Add a2wsgi wrapper to `src/main.py`

**Files:**
- Modify: `d4g-backend/src/main.py`

- [ ] **Step 1: Add import and wrap app**

```python
# At the top of d4g-backend/src/main.py
from a2wsgi import ASGIMiddleware

# ... (existing imports and code)

# At the bottom of d4g-backend/src/main.py
app = create_app()

# PythonAnywhere WSGI wrapper
wsgi_app = ASGIMiddleware(app)
```

- [ ] **Step 2: Verify locally**

Run: `uv run uvicorn src.main:app --reload`
Expected: App starts and handles requests at http://localhost:8000.

- [ ] **Step 3: Commit**

```bash
git add d4g-backend/src/main.py
git commit -m "feat: add a2wsgi wrapper to src/main.py for PythonAnywhere support"
```

### Task 2: Update `wsgi.py` to use the wrapper from `src/main.py`

**Files:**
- Modify: `d4g-backend/wsgi.py`

- [ ] **Step 1: Update wsgi.py to import from src.main**

```python
import os
import sys

# Add the current directory to sys.path so the 'src' package is discoverable
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

from src.main import wsgi_app as application

# This 'application' object is what PythonAnywhere looks for in your configuration
# It is now imported directly from src.main to keep the wrapper logic centralized.
```

- [ ] **Step 2: Verify by running a simple python script to check imports**

Run: `python3 -c "from wsgi import application; print('WSGI application loaded successfully')"`
Expected: Output "WSGI application loaded successfully".

- [ ] **Step 3: Commit**

```bash
git add d4g-backend/wsgi.py
git commit -m "refactor: update wsgi.py to use wsgi_app from src.main"
```

### Task 3: Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `pytest d4g-backend/tests`
Expected: All tests PASS.

- [ ] **Step 2: Cleanup and Final Commit**

```bash
# Ensure everything is clean
git status
```
