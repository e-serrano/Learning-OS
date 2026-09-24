# Learning OS

A local-first, AI-assisted learning system built around one canonical loop:

```text
GOAL → DIAGNOSE → 80/20 → ROADMAP → LEARN → PRACTICE → FEEDBACK → ADAPT
     → CONSOLIDATE → REVIEW → TRANSFER → PROJECT → EVALUATE → REPEAT
```

Architecture principle:

> AI proposes. The Learning Engine decides. SQLite records evidence. Obsidian preserves durable knowledge.

## Quick start (Docker)

Requires [Docker](https://docs.docker.com/get-docker/) (Compose is bundled
with Docker Desktop).

```bash
git clone https://github.com/e-serrano/Learning-OS.git
cd Learning-OS
cp .env.docker.example .env
```

Edit `.env` — two values are required, both explained inline in the file:

- `VAULT_HOST_PATH` — path on your machine to an Obsidian vault (or any
  folder of Markdown files).
- `KEYRING_CRYPTFILE_PASSWORD` — encrypts AI provider credentials at rest.
  Generate one *before* starting anything, in a regular terminal on your
  machine (Git Bash/macOS/Linux; a PowerShell equivalent is in
  [DEVELOPMENT.md](DEVELOPMENT.md#docker) if that's all you have):

  ```bash
  openssl rand -base64 32
  ```

Then bring the stack up:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8080` and complete onboarding: vault path (enter
`/vault`, not your host path — see why in
[DEVELOPMENT.md](DEVELOPMENT.md#docker)), then an AI provider and, if it
needs one, an API key. Both services are published to `127.0.0.1` only.

Manage it from the same directory afterward:

```bash
docker compose down       # stop -- your data (DB + credentials) persists
docker compose down -v    # stop AND delete the database + stored credentials
docker compose up -d      # start again in the background
git pull && docker compose up --build   # update to the latest version
```

See [DEVELOPMENT.md](DEVELOPMENT.md#docker) for the optional bundled
Ollama profile, troubleshooting, and the native (non-Docker) setup.

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

See [DEVELOPMENT.md](DEVELOPMENT.md) for native (non-Docker) installation,
the onboarding walkthrough, supported AI providers, testing, and
troubleshooting. [CONTRIBUTING.md](CONTRIBUTING.md) covers branch/commit
conventions.

## Status

All 143 tasks in `docs/TASKS.md` are done, including Phase 11 (advanced
learning: FSRS, knowledge graph UI, Socratic/interview tutor chat,
teach-back mode, voice, browser extension, Obsidian plugin, SQL sandbox,
git integration) and Docker packaging.
