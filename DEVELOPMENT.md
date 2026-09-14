# Development environment

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm

## Setup

```bash
cp .env.example .env
```

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

Runs at `http://127.0.0.1:8000` (loopback only — see `docs/API_SPEC.md` §12).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Quality gates

Run before every commit (see `CONTRIBUTING.md`):

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy app
cd frontend && npm test && npm run build
```

## Credentials

AI provider API keys are never placed in `.env`, source, or the database.
They are entered during onboarding and stored via the OS keyring; only a
`credential_ref` is persisted locally.
