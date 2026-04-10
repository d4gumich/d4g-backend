# Data4Good-UMich Backend

A restructured, domain-based FastAPI backend for processing humanitarian reports and providing intelligent search and chatbot capabilities.

## 🚀 Overview

This backend integrates several sub-projects into a unified API:
- **Chetah:** Advanced search using BM25 and BM25F algorithms.
- **Hangul:** PDF analysis, metadata extraction, language detection, and theme/disaster prediction.
- **Lighthouse:** Integration with HuggingFace Spaces for resume/skill extraction.
- **Owl:** RAG (Retrieval-Augmented Generation) chatbot for ReliefWeb data.
- **Summary:** AI-powered text summarization using Google Gemini.

## 🏗️ Architecture

The project follows a **Domain-Based** (Feature-First) architecture:
- `src/core/`: Global settings and configuration.
- `src/shared/`: Common utilities and ML models.
- `src/modules/`: (Logical grouping) Each feature has its own folder containing its router, service, and schemas.
- `tests/`: Automated tests mirroring the source structure.

## 🛠️ Tech Stack

- **Framework:** FastAPI
- **Dependency Management:** [uv](https://github.com/astral-sh/uv)
- **Validation:** Pydantic v2
- **ML/NLP:** SpaCy, scikit-learn, PyTorch, HuggingFace
- **Database:** PostgreSQL (for Owl)
- **Quality:** Ruff (Linter/Formatter), Mypy (Type Checker), Pytest

## 🚦 Getting Started

### Prerequisites
- Python 3.10+
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation
1. Clone the repository.
2. Sync dependencies:
   ```bash
   uv sync
   ```
3. Set up your `.env` file (copy from `.env.example`). **Never commit your `.env` file.**

### 🛠️ Development & Debug Mode
To enable verbose output and detailed error messages during development:
1. In your `.env` file, set `DEBUG=True`.
2. When `DEBUG` is enabled, failed requests will return a full stack trace in the JSON response to help diagnose issues.
3. You can also adjust `LOG_LEVEL` (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`) in the `.env` file.

### Running the App
```bash
uv run uvicorn src.main:app --reload
```
The API will be available at `http://localhost:8000`.
Swagger UI documentation: `http://localhost:8000/docs`

### Running Tests
```bash
uv run pytest
```

## 🧹 Quality Control
We use `pre-commit` to ensure code quality.
```bash
uv run pre-commit install
uv run ruff check .
uv run mypy src/
```

## 📄 License
This project is for Data4Good @ UMich.
