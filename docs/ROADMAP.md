# ROADMAP.md

# Learning OS — Executable Implementation Roadmap

## Phase 0 — Repository bootstrap

Deliver:

- Python backend
- frontend shell
- SQLite connection
- migrations
- typed configuration
- logging
- test framework
- lint/format/type checking
- `.env.example`
- README

Acceptance:

```text
pytest passes
backend starts locally
frontend starts locally
SQLite migration creates schema
```

---

## Phase 1 — Obsidian foundation

Tasks:

1. Vault path configuration.
2. Recursive Markdown scanner.
3. Ignore rules.
4. Frontmatter parser.
5. Managed-section parser.
6. Content hashing.
7. Vault index.
8. Conflict detection.
9. Atomic writes.
10. Diff generation.

Acceptance:

- scan a real vault without modifying it
- detect external file changes
- modify only managed regions
- preserve user text byte-for-byte where possible

---

## Phase 2 — Domain + persistence

Implement:

- goals
- concepts
- skills
- relations
- sessions
- activities
- exercises
- attempts
- evaluations
- evidence
- mistakes
- reviews
- AI runs

Acceptance:

- migrations run from empty DB
- repositories have unit tests
- domain services do not import UI/framework code

---

## Phase 3 — AI abstraction

Implement:

```text
AIProvider
OpenAI-compatible adapter
Ollama adapter
Mock adapter
```

Implement structured response validation.

Acceptance:

- mock provider can run full learning session
- invalid output is rejected
- provider can be swapped without changing learning engine

---

## Phase 4 — Diagnostic + 80/20

Implement:

```text
goal
→ diagnostic
→ evidence
→ high-leverage analysis
→ roadmap
```

Acceptance:

A new goal produces:

- diagnostic questions
- initial knowledge map
- prioritized concepts
- dependency roadmap

---

## Phase 5 — Learning session

Implement:

- session planner
- tutor
- exercise generator
- answer submission
- evaluator
- hints
- adaptive next activity

Acceptance:

A user can complete a 30-minute guided session without manually orchestrating prompts.

---

## Phase 6 — Knowledge consolidation

Implement:

- mastery calculation
- mistake tracking
- Obsidian curator
- diff/approval
- session summary
- concept note updates

Acceptance:

After a session:

```text
evidence exists
mastery changes
mistakes update
Obsidian proposal appears
user approves
Markdown changes safely
```

---

## Phase 7 — Reviews

Implement:

- due review query
- basic spaced repetition
- review session
- retention update

Acceptance:

Weak/high-importance concepts become review candidates and completed reviews schedule future reviews.

---

## Phase 8 — Projects + transfer

Implement:

- project generation
- project tasks
- transfer exercises
- final assessment

Acceptance:

A goal can progress from fundamentals to an integrated practical project and independent assessment.

---

## Phase 9 — UI

Implement:

- dashboard
- goal view
- roadmap
- learning session
- knowledge explorer
- reviews
- projects
- vault changes/diff

Do not build advanced analytics before the core loop works.

---

## Phase 10 — Advanced retrieval

Only after MVP:

- SQLite FTS
- embeddings
- semantic retrieval
- relevance scoring
- context inspection

---

## Phase 11 — Advanced learning

Future:

- FSRS
- knowledge graph UI
- interview mode
- Socratic mode
- teach-back mode
- voice
- browser extension
- Obsidian plugin
- code execution sandbox
- Git integration

---

## Phase 0.5 — GitHub + onboarding

Before the first full learning loop, establish the GitHub repository, branch/PR workflow and CI, then implement resumable onboarding for the Obsidian vault and AI provider. The normal user path must not require editing `.env` files or source code.

Onboarding must support Ollama, OpenAI, Anthropic/Claude, OpenRouter, NVIDIA NIM/API and generic OpenAI-compatible endpoints through explicit adapters and secure credential storage.
