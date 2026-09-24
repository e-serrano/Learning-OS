# Development environment

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js ^22.22.2 || ^24.15.0 || >=26.0.0 (see `frontend/package.json`
  `engines`; CI pins `22.22.2`) and npm
- An Obsidian vault (or any plain folder of Markdown files) to point Learning OS at during onboarding
- Optionally, an API key for one AI provider (OpenAI, Anthropic, OpenRouter, NVIDIA NIM) or a local [Ollama](https://ollama.com) install — the bundled Mock provider needs neither and is enough to explore the app

## Installation

```bash
cp .env.example .env
```

`.env` only holds process-level infrastructure settings (loopback host/port,
database path, log level) — never AI credentials. See
[Credentials](#credentials) below.

### Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

`alembic upgrade head` creates/updates the SQLite schema (including
`app_settings`/`ai_provider_configs` — onboarding will fail with "no such
table" without it). Re-run it after pulling migrations added by others.

Runs at `http://127.0.0.1:8000` (loopback only — see `docs/API_SPEC.md` §12).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://127.0.0.1:5173`. `backend/app/main.py` only allows CORS
requests from this origin (and `localhost:5173`) by default — running the
frontend on a different port means every API call will fail CORS, unless you
override it with `LEARNINGOS_CORS_ORIGINS` (comma-separated, see
`.env.example`).

## Docker

An alternative to the native setup above — one command brings up both
services, backed by SQLite/credential storage that survive container
restarts (docs/TASKS.md T143).

```bash
cp .env.docker.example .env
# edit .env: VAULT_HOST_PATH (your vault's path on THIS machine) and
# KEYRING_CRYPTFILE_PASSWORD (see below)
docker compose up --build
```

`KEYRING_CRYPTFILE_PASSWORD` is generated once, on your host, in a regular
terminal — no container is running yet at this point, so it isn't run
"inside Docker" or "inside CMD" specifically:

```bash
openssl rand -base64 32
```

Works as-is in a macOS/Linux terminal or Windows Git Bash (bundled with Git
for Windows — the same shell most `git`/`npm`/`uv` commands in this guide
assume). Plain Windows `cmd.exe` has no equivalent built in; use PowerShell
instead:

```powershell
-join ((48..57)+(65..90)+(97..122)|Get-Random -Count 32|%{[char]$_})
```

That brings up the two containers — it does **not** finish setup by itself.
Open `http://127.0.0.1:8080` and go through onboarding same as a native
install ([Onboarding](#onboarding) below): vault path, then AI provider,
then (if the provider needs one) its API key. `KEYRING_CRYPTFILE_PASSWORD`
only prepares *where* that key gets encrypted at rest — it is not the key
itself and doesn't skip this step.

Frontend at `http://127.0.0.1:8080`, backend at `http://127.0.0.1:8000`. Both
are published to `127.0.0.1` only, matching `docs/AGENTS.md` #19 — this is a
local-first, single-user tool with AI credentials and vault filesystem
access, not something to expose to a network by default.

A few things work differently than the native setup:

- **CORS never comes up.** `frontend/nginx.conf` reverse-proxies `/api/` to
  the backend container, so the browser only ever talks to one origin.
- **Vault path is fixed before startup, not chosen in the wizard.** A
  container only ever sees folders explicitly bind-mounted into it —
  Docker has no mechanism for a running container to reach out and mount
  an arbitrary host path *after* it's already up, so typing a host path
  into onboarding (the way native installs work) can't work here.
  `VAULT_HOST_PATH` (in `.env`, read before the container starts) is the
  bind mount; the wizard just points at where it landed inside the
  container (`/vault`), never your real host path. Switching vaults means
  editing `.env` and `docker compose up` again, not re-running onboarding.
  (A single mounted folder is also the smallest filesystem exposure the
  container gets — mounting something broader like your whole home
  directory would let onboarding pick any subfolder without touching
  `.env` again, at the cost of the container being able to see everything
  under it, not just the vault. Not done here — see `docs/AGENTS.md` #19
  on restricting filesystem access — but it's a legitimate trade-off if
  you want that convenience instead.)
- **Credentials.** There is no OS keyring inside a Linux container, so
  `KEYRING_CRYPTFILE_PASSWORD` activates an encrypted-file backend instead
  (`app/config/keyring_setup.py`) — a no-op on native runs, where the real
  OS keyring is used exactly as documented above.
- **Ollama.** Not started by default. Either point the `ollama` provider's
  base URL at an Ollama already running on your host
  (`http://host.docker.internal:11434`), or run the bundled optional
  service with `docker compose --profile ollama up` and use
  `http://ollama:11434` instead.

`docker compose down` stops both containers without losing data (named
volumes); add `-v` to also delete the database and stored credentials.

## Onboarding

The first time you open the frontend (or whenever `GET /onboarding/status`
hasn't reached `COMPLETE`), you land in the onboarding wizard instead of the
app shell. It walks through, in order:

1. **Vault** — a filesystem path to an Obsidian vault (or plain folder of
   `.md` files). Validated read-only before anything is saved.
2. **Provider** — pick one of the 7 registered providers (see
   [Providers](#providers)) and, if it needs one, a base URL.
3. **Credential/Model** — model name, and an API key if the provider needs
   one. "Test connection" sends the key once to validate it, stores it in
   the OS keyring, and never keeps it in the browser or the database (see
   `docs/TASKS.md` T124).
4. **Finish** — marks onboarding `COMPLETE` and hands off to the app shell.

From there, creating your first learning goal (Dashboard → "New goal") is
what actually drives the canonical loop: GOAL → DIAGNOSE → 80/20 → ROADMAP →
LEARN → ... (see `docs/SPECS.md` §1).

## Providers

| id                   | display name           | needs API key | needs base URL | notes                                  |
| -------------------- | ----------------------- | :-----------: | :-------------: | --------------------------------------- |
| `mock`                | Mock (offline)          |      no       |       no        | deterministic, no network — default for local dev/CI |
| `ollama`               | Ollama (local)          |      no       |    yes (default `http://localhost:11434`) | needs a running local Ollama install |
| `openai`               | OpenAI                  |      yes      |       no        |                                          |
| `anthropic`            | Anthropic / Claude      |      yes      |       no        | native Messages API, not OpenAI-compatible |
| `openrouter`           | OpenRouter               |      yes      |    yes (default `https://openrouter.ai/api/v1`) |                        |
| `nvidia_nim`           | NVIDIA NIM/API           |      yes      |       yes        | self-hosted or hosted NIM, no default URL |
| `openai_compatible`    | OpenAI-compatible        |      no (optional) |    yes        | any Chat Completions-compatible endpoint |

Full descriptors (including `supports_model_listing`/`supports_structured_output`)
are served live at `GET /api/v1/providers`; the source of truth is
`backend/app/ai/provider_registry.py`.

A configured provider is only ever confirmed reachable when you actually hit
"Test connection" during onboarding, or `POST /api/v1/providers/validate` —
nothing assumes a provider works just because it's configured
(`docs/AI_CONTRACTS.md` #19).

## Browser extension

`extension/` (docs/TASKS.md T135) is a Manifest V3 web clipper: right-click a
text selection on any page → "Save selection to Learning OS" → it lands as a
pending `ChangeProposal` under `Clippings/` (`POST /api/v1/vault/clip`), reviewed
and applied through the exact same Vault diff UI as any other proposal
(`docs/API_SPEC.md` #2). No popup, no options page — feedback is a toolbar
badge (green tick / red "ERR") that clears itself after a few seconds.

To load it locally:

1. Configure a vault and start the backend (`uv run uvicorn app.main:app --reload`
   — the extension hardcodes port 8000, the documented default).
2. Chrome/Edge → `chrome://extensions` → enable Developer mode → "Load
   unpacked" → select the `extension/` directory.
3. Select text on any page, right-click, choose "Save selection to Learning
   OS", then check the Vault diff UI for the pending clip.

The background service worker fetches the local API directly — its
`host_permissions` make MV3 background contexts exempt from CORS, so the
backend's `allow_origins` (locked to the Vite dev origin) never needed to
change for this. Firefox support (a different manifest key set for MV3
service workers) and a configurable API base URL (currently hardcoded) are
natural follow-ups, not attempted here.

## Obsidian plugin

`obsidian-plugin/` (docs/TASKS.md T136) adds a sidebar pane inside Obsidian
itself listing pending `ChangeProposal`s (`GET /api/v1/vault/changes`) with
Apply/Reject buttons — the exact same review/apply/reject actions the web
frontend's Vault diff UI exposes, brought into the tool where the notes
actually live instead of a separate browser tab. Hand-written plain
JavaScript, no bundler/TypeScript build step (Obsidian loads `main.js`
directly via CommonJS `require`) — same "no new build tooling for something
this small" choice T135 made for the browser extension.

To load it locally:

1. Configure a vault and start the backend (hardcodes port 8000, same
   assumption the browser extension makes).
2. Copy (or symlink) `obsidian-plugin/` into
   `<vault>/.obsidian/plugins/learning-os-pending-changes/`.
3. In Obsidian: Settings → Community plugins → enable "Learning OS: Pending
   Changes". A ribbon icon and the "Open pending changes" command both open
   the sidebar pane.

Uses Obsidian's own `requestUrl` API instead of `fetch` — Obsidian's docs
recommend it specifically because it bypasses the renderer's CORS
enforcement, the same reasoning behind T135's background-service-worker
routing. A configurable base URL (settings tab) is a natural follow-up, not
attempted here.

## Testing

Five test suites cover different layers (`docs/AGENTS.md` §15). `uv run pytest`
collects everything under `backend/tests/` in one run — unit, integration,
the canonical-loop E2E, *and* the live provider smoke tests; the live ones
just always skip themselves unless you opt in (see below), so a plain
`uv run pytest` is still the one command that runs the whole backend suite:

| Suite | Where | Runs by default | Runs in CI |
| --- | --- | :---: | :---: |
| Backend unit/integration | `backend/tests/{ai,api,config,domain,obsidian,onboarding,persistence,services}/` | yes | yes |
| Backend canonical-loop E2E | `backend/tests/e2e/` | yes | yes |
| Live AI provider smoke | `backend/tests/live/` | collected, but skips without credentials | collected, always skips |
| Frontend unit | `frontend/src/**/*.test.tsx`, run via `npm test` | yes | yes |
| Browser fresh-install E2E | `frontend/e2e/` (Playwright), run via `npm run test:e2e` | opt-in | yes, separate `e2e` CI job (boots a real backend + frontend) |

The live provider suite (`docs/TASKS.md` T122) makes one real network call
per adapter against the actual provider API, gated behind its own
`LEARNINGOS_LIVE_*` env vars — nothing in CI has real credentials, so these
always skip there. To run one locally:

```bash
cd backend
LEARNINGOS_LIVE_OPENAI_API_KEY=sk-... LEARNINGOS_LIVE_OPENAI_MODEL=gpt-4o-mini \
    uv run pytest tests/live -v
```

See `backend/tests/live/test_provider_smoke.py`'s module docstring for every
provider's required variables.

## Quality gates

Run before every commit (see `CONTRIBUTING.md`):

```bash
cd backend && uv run ruff format && uv run ruff check --fix . && uv run pytest -q && uv run mypy app
cd frontend && npm test && npm run build && npm run lint
```

## Credentials

AI provider API keys are never placed in `.env`, source, or the database.
They are entered during onboarding and stored via the OS keyring; only a
`credential_ref` (an opaque lookup key, not the secret) is persisted locally
(`docs/TASKS.md` T014, T124).

## Troubleshooting

**`no such table: app_settings` on first request.** Migrations haven't run.
`cd backend && uv run alembic upgrade head`.

**Frontend requests fail with a CORS error.** The frontend isn't running on
`http://localhost:5173`/`http://127.0.0.1:5173`, or the backend isn't running
at all. `app/main.py` only allows those two origins.

**`AI_UNAVAILABLE` when generating a roadmap/exercise/etc.** Either no
provider is configured yet (finish onboarding), or the configured
provider's credential/base URL is wrong — re-run onboarding's "Test
connection" step, or `POST /api/v1/providers/validate`. If you're using
`ollama`, confirm the local server is actually running at the configured
base URL.

**`VAULT_UNAVAILABLE`.** The configured vault path doesn't exist, isn't a
directory, or isn't readable from the account running the backend. Vault
paths are validated on every use, not just at onboarding time.

**Onboarding won't advance past "Test connection".** The provider rejected
the credential/model — check `reason` in the failed response. The API key
field always clears itself after each attempt (`docs/TASKS.md` T124),
success or failure, so you'll need to retype it.

**`uv: command not found`.** `uv` isn't on `PATH`; see the
[uv install docs](https://docs.astral.sh/uv/getting-started/installation/).

**Backend port 8000 (or frontend port 5173) already in use.** Another
process is bound to it — `uvicorn app.main:app --reload --port <other>` (and
update the CORS origin / API base URL if you do), or stop the other process.

**Windows: OS keyring errors when saving a credential.** The `keyring`
library uses Windows Credential Manager by default and should work
out of the box; if it doesn't, check that Credential Manager itself is
reachable (some locked-down/managed machines restrict it).

**Docker: `VAULT_UNAVAILABLE` even though the vault exists on your host.**
Onboarding needs the path as it appears *inside the container* — enter
`/vault` (the mount point `docker-compose.yml` sets up), not your host path.

**Docker: `variable is not set` when running `docker compose up`.**
`VAULT_HOST_PATH`/`KEYRING_CRYPTFILE_PASSWORD` are required, not optional —
`cp .env.docker.example .env` and fill them in first.

**Docker: `AI_UNAVAILABLE` with `ollama` configured.** Inside the backend
container, `http://localhost:11434` means the backend container itself, not
your host or the optional `ollama` Compose service — use
`http://host.docker.internal:11434` (host-installed Ollama) or
`http://ollama:11434` (the `--profile ollama` service).

## Architecture

```text
UI (React) → API (FastAPI routes) → Application services → Domain
                                          ↕            ↕
                                    Persistence      Obsidian
                                          ↕
                                          AI
```

- **Domain**: pure entities/enums/value objects, no I/O (`backend/app/domain/`).
- **Application services**: orchestrate domain + ports; this is where
  "AI proposes, the Learning Engine decides" is enforced — AI output is
  never written to `Concept.mastery`/`.status` directly, only derived from
  persisted `Evidence` (`backend/app/services/`).
- **Persistence**: SQLite via SQLAlchemy Core, evidence/state of record
  (`backend/app/persistence/`).
- **Obsidian**: read-only scanning plus a validate-then-write change-proposal
  pipeline for any Markdown edit — no AI-generated content ever touches disk
  without going through `ProposalValidator` and an explicit user approval
  (`backend/app/obsidian/`).
- **AI**: provider-agnostic orchestrator + adapters, structured output only,
  never raw text (`backend/app/ai/`).

Full architectural rules live in `docs/AGENTS.md`; the normative behavior
spec is `docs/SPECS.md`; the API contract is `docs/API_SPEC.md`.
