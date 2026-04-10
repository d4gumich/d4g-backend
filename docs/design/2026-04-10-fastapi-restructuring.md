# Design Doc: Domain-Based FastAPI Restructuring

**Date:** 2026-04-10  
**Status:** Draft / Pending Review  

## 1. Problem Statement
The current Flask-based backend (`wsgi.py`) has grown into a large monolith where multiple sub-projects (Chetah, Hangul, Lighthouse, Owl) are tightly coupled in a single file. This makes onboarding difficult, prevents independent scaling/migration to GCP, and lacks modern features like automatic type validation and documentation.

## 2. Proposed Solution
Migrate the backend to **FastAPI** using a **Domain-Based** (Feature-First) architecture. This separates each sub-project into its own isolated module (`src/chetah`, `src/hangul`, etc.), preparing the codebase for a microservices transition on GCP while maintaining a clean, well-tested "modular monolith" for now.

## 3. Architecture Overview

### 3.1 Directory Structure
```text
d4g-backend/
├── pyproject.toml              # Unified config for Ruff, Mypy, Pytest
├── .pre-commit-config.yaml     # Hooks for linting and formatting
├── src/
│   ├── main.py                 # FastAPI application and root router
│   ├── core/                   # Global configuration (Settings, Logging)
│   ├── shared/                 # Common utilities (CleanText, sanitizer)
│   ├── chetah/                 # Sub-project: Chetah (v1/v2)
│   │   ├── router.py           # FastAPI routes
│   │   ├── service.py          # Business logic
│   │   ├── schemas.py          # Pydantic models (Request/Response)
│   │   └── utils.py            # Chetah-specific helpers
│   ├── hangul/                 # Sub-project: Hangul (Detection)
│   ├── lighthouse/             # Sub-project: Lighthouse (HF Space)
│   ├── owl/                    # Sub-project: Owl (Chatbot)
│   └── summary/                # Sub-project: Summary
└── tests/                      # Mirrored structure for unit/integration tests
```

### 3.2 Framework Selection: FastAPI
- **Pydantic Validation:** Ensures all incoming and outgoing data is strictly typed.
- **Auto-Docs:** Swagger UI available at `/docs` for easier onboarding.
- **Async Support:** Improves performance for I/O-bound tasks (e.g., calling Lighthouse API).

## 4. Implementation Plan

### Phase 1: Tooling & Quality Standards
- Update `pyproject.toml` with `fastapi`, `uvicorn`, `ruff`, `mypy`, and `pytest`.
- Configure `ruff` for consistent formatting and `mypy` for static typing.
- Setup `pre-commit` to catch errors before they reach the repository.

### Phase 2: Core Infrastructure
- Initialize `src/main.py` with the FastAPI app and CORS.
- Set up `src/core/config.py` using `pydantic-settings` to handle `.env` and `configuration.ini`.
- Add a root health-check endpoint and basic test.

### Phase 3: Incremental Domain Migration
Each domain (Chetah, Hangul, etc.) will be migrated one-by-one:
1.  **Chetah:** Move `search` logic and define v1/v2 schemas.
2.  **Hangul:** Handle `UploadFile` payloads for PDF analysis.
3.  **Lighthouse:** Move client logic for HuggingFace interactions.
4.  **Owl & Summary:** Move remaining chatbot and summarization logic.

### Phase 4: Shared Cleanup & Removal
- Relocate general scripts (e.g., `CleanText.py`, `sanitizer.py`) to `src/shared/`.
- Update all internal imports.
- Delete the old `wsgi.py` and remove Flask dependencies.

### Phase 5: Verification
- Ensure 100% pass rate on `pytest`.
- Fix any remaining `ruff` or `mypy` warnings.
- Manually verify `/docs` endpoints.

## 5. Success Criteria
- [ ] No Flask dependencies remain.
- [ ] Sub-projects are isolated in their own folders.
- [ ] `ruff` and `mypy` pass without errors.
- [ ] All existing endpoints are functional and tested in the new FastAPI structure.
