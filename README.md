# Learning OS

A local-first, AI-assisted learning system built around one canonical loop:

```text
GOAL → DIAGNOSE → 80/20 → ROADMAP → LEARN → PRACTICE → FEEDBACK → ADAPT
     → CONSOLIDATE → REVIEW → TRANSFER → PROJECT → EVALUATE → REPEAT
```

Architecture principle:

> AI proposes. The Learning Engine decides. SQLite records evidence. Obsidian preserves durable knowledge.

## Structure

```text
backend/          FastAPI application, domain/services/persistence/AI orchestration
frontend/         React + TypeScript UI
extension/        Browser web clipper (Manifest V3) -- see DEVELOPMENT.md
obsidian-plugin/  Obsidian sidebar plugin for reviewing pending vault changes
docs/             Normative specification (source of truth)
scripts/          Reserved for developer/operations scripts (currently empty)
```

## Documentation

Start with [docs/SPECS.md](docs/SPECS.md). The execution backlog lives in
[docs/TASKS.md](docs/TASKS.md); [docs/AGENTS.md](docs/AGENTS.md) defines the
coding-agent contract for this repository.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for installation, the onboarding
walkthrough, supported AI providers, testing, and troubleshooting.
[CONTRIBUTING.md](CONTRIBUTING.md) covers branch/commit conventions.

## Running with Docker

```bash
cp .env.docker.example .env   # fill in VAULT_HOST_PATH and KEYRING_CRYPTFILE_PASSWORD
docker compose up --build
```

Frontend at `http://127.0.0.1:8080`, backend at `http://127.0.0.1:8000`, both
loopback-only by default. See DEVELOPMENT.md's "Docker" section for details.

## Status

All 143 tasks in `docs/TASKS.md` are done, including Phase 11 (advanced
learning: FSRS, knowledge graph UI, Socratic/interview tutor chat,
teach-back mode, voice, browser extension, Obsidian plugin, SQL sandbox,
git integration) and Docker packaging (this section).
