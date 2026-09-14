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
