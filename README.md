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

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup and [CONTRIBUTING.md](CONTRIBUTING.md)
for branch/commit conventions and quality gates.

## Status

Early bootstrap. See `docs/TASKS.md` for current progress.
