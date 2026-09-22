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
backend/    FastAPI application, domain/services/persistence/AI orchestration
frontend/   React + TypeScript UI
scripts/    Developer/operations scripts
docs/       Normative specification (source of truth)
```

## Documentation

Start with [docs/SPECS.md](docs/SPECS.md). The execution backlog lives in
[docs/TASKS.md](docs/TASKS.md); [docs/AGENTS.md](docs/AGENTS.md) defines the
coding-agent contract for this repository.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for installation, the onboarding
walkthrough, supported AI providers, testing, and troubleshooting.
[CONTRIBUTING.md](CONTRIBUTING.md) covers branch/commit conventions.

## Status

MVP in progress: 123/138 tasks done (`docs/TASKS.md`). Phases 0-11 (bootstrap
through the full frontend) are complete; Phase 12 (Release MVP — E2E tests,
security audits, this documentation pass, then a `v0.1.0` tag) is the current
phase. Phase 13 (post-MVP, including FSRS-based scheduling) hasn't started.
