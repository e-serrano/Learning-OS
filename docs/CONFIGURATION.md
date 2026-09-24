# Learning OS — CONFIGURATION.md

## User-facing configuration

Learning OS is local-first and should be usable without editing source code.

### Vault

`vault_path` points to the local Obsidian vault root. It is validated on configuration and scanned read-only before any write is possible.

### AI provider

Supported provider IDs:

- `ollama`
- `openai`
- `anthropic`
- `openrouter`
- `nvidia_nim`
- `openai_compatible`
- `mock`

Each provider has its own adapter and capability declaration.

### Credentials

API credentials use the OS keyring/credential store. The application database stores only `credential_ref`.

### Model

Model IDs are configuration, not hard-coded business logic. If a provider can list models, the UI may expose the returned list; otherwise the user enters the model ID.

### Onboarding

```text
WELCOME
→ VAULT
→ VAULT_SCAN
→ AI_PROVIDER
→ CREDENTIAL
→ MODEL
→ VALIDATE
→ FIRST_GOAL
→ COMPLETE
```

Onboarding is resumable and reconfigurable.

### Language

`language` steers both the UI's own copy and every AI-generated response
(tutor, exercises, evaluator feedback, and Obsidian note content the
curator writes) into one of a closed set of supported languages -- see
`docs/AI_CONTRACTS.md` #2. Unlike the settings above, it is not part of
onboarding: readable/writable at any time via `GET`/`PATCH /settings`
(`docs/API_SPEC.md` #15), before or after onboarding completes.

### Git auto-commit

Opt-in, off by default: when the configured vault is itself a git
repository, `git_auto_commit` makes every vault write the app applies
(docs/AGENTS.md #22) also land as its own git commit, one file per
commit, never the whole working tree. Also configured via
`GET`/`PATCH /settings` (`docs/API_SPEC.md` #15), independent of
onboarding.

### Process-level settings

Host/port, database path, CORS origins and log level are infrastructure
configuration, not user-facing application state -- set via environment
variables (`LEARNINGOS_*`, see `.env.example`) rather than onboarding or
`/settings`. Docker deployment (`DEVELOPMENT.md` "Docker") adds two more:
`VAULT_HOST_PATH` (the vault bind mount) and `KEYRING_CRYPTFILE_PASSWORD`
(encrypts credentials at rest where no OS keyring exists, i.e. inside a
Linux container).
