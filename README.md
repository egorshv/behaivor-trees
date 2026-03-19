# Behavior Trees Editor MVP

Single-user local editor for `behavior trees` with a drag-and-drop React UI and a FastAPI backend powered by `py_trees`.

## Stack
- Backend: `FastAPI`, `SQLAlchemy`, `py_trees`, `SQLite`
- Frontend: `React`, `TypeScript`, `Vite`, `React Flow`

## Features
- Visual editor with drag from palette into a canvas
- Node property inspector
- Save/load/delete trees in SQLite
- Server-side validation
- Run, tick, and reset execution sessions
- Persisted per-node runtime status
- Seeded demo tree on first backend start

## Project Layout
```text
backend/
  app/
  tests/
frontend/
  src/
```

## Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The backend defaults to `backend/data/behavior_trees.db`.

## Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend expects the API at `http://localhost:8000`. Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Tests
Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm test
```
