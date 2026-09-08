# Vehicle C2 Node

This repository is a scaffold for the Vehicle C2 Node described in AGENT.md. It contains a FastAPI backend, HTMX-driven frontend templates, and Docker support.

Quick start (local):

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or with Docker Compose:

```bash
docker compose up --build -d
```
