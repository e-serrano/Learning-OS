
---

# 31. Repository, GitHub and onboarding

The repository itself is part of the product implementation. Bootstrap Git, create/configure the GitHub remote, add CI, define the branch/PR workflow and protect `main` where practical.

The first-run application flow is:

```text
WELCOME → VAULT → VAULT_SCAN → AI_PROVIDER → CREDENTIAL → MODEL → VALIDATE → FIRST_GOAL → COMPLETE
```

Vault onboarding is read-only. AI onboarding uses a provider registry with explicit adapters for:

```text
Ollama
OpenAI
Anthropic / Claude
OpenRouter
NVIDIA NIM/API
OpenAI-compatible
Mock
```

Non-secret configuration is persisted locally. API credentials are stored through the OS keyring/credential facility and referenced by ID; they are never stored in SQLite, Markdown, Git, logs or browser storage.

Provider validation checks endpoint, credential, model and required structured-output capability. Anthropic/Claude and NVIDIA are not assumed to share OpenAI semantics merely because compatible wrappers may exist.

The implementation backlog for this section is normative in `TASKS.md`.
