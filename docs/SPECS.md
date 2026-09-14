# SPECS.md

# Learning OS — Executable Product Specification

## 1. Product contract

Learning OS is a local-first adaptive learning system.

Its canonical loop is:

```text
GOAL
→ DIAGNOSE
→ 80/20
→ ROADMAP
→ LEARN
→ PRACTICE
→ FEEDBACK
→ ADAPT
→ CONSOLIDATE
→ REVIEW
→ TRANSFER
→ PROJECT
→ EVALUATE
→ REPEAT
```

The system must maintain persistent learning state and use the user's Obsidian vault as the durable, inspectable knowledge layer.

---

## 2. MVP success criterion

A new user must be able to:

```text
select vault
→ create goal
→ diagnostic
→ 80/20 analysis
→ roadmap
→ guided session
→ attempt exercise
→ receive feedback
→ update evidence/mastery
→ record mistakes
→ approve Obsidian update
→ receive review
→ continue later
→ complete transfer assessment
```

If any of these steps requires manually copying prompts between tools, the MVP is incomplete.

---

## 3. Architecture

```text
React/TypeScript UI
        │
        ▼
FastAPI local API
        │
        ├── Learning Engine
        ├── Knowledge Engine
        ├── Assessment Engine
        ├── Scheduling Engine
        ├── Obsidian Engine
        └── AI Orchestrator
                │
                ▼
          AI Provider Adapter
                │
        ┌───────┴────────┐
        ▼                ▼
   Remote model      Local model

FastAPI
   ├── SQLite
   └── Obsidian filesystem
```

Domain logic must remain framework-independent.

---

## 4. Required contracts

The implementation must conform to:

- `DOMAIN_MODEL.md`
- `DATABASE_SCHEMA.md`
- `OBSIDIAN_SCHEMA.md`
- `AI_CONTRACTS.md`
- `API_SPEC.md`
- `AGENTS.md`
- `ROADMAP.md`

These documents are normative.

---

## 5. Technology baseline

Preferred MVP:

```text
Backend: Python 3.13+
API: FastAPI
Validation: Pydantic
Database: SQLite
ORM/query layer: SQLAlchemy or SQLModel
Frontend: React + TypeScript + Vite
```

Provider adapters:

```text
OpenAI-compatible
Ollama
Mock
```

---

## 6. Knowledge architecture

Obsidian contains durable human-readable knowledge.

SQLite contains:

- evidence
- attempts
- evaluations
- schedules
- operational state
- indexes
- cached metadata

Raw evidence must never be lost when derived algorithms change.

---

## 7. Learning state

Track independently:

```text
mastery      0..5
confidence   0..100
retention    0..100
importance   1..5
```

Also track:

```text
mistakes
evidence
practice history
transfer performance
independence
```

---

## 8. Mastery rules

Mastery is derived.

No single interaction may mark a concept mastered.

Mastery should require repeated evidence across:

- time
- difficulty
- contexts
- transfer
- independent performance

The exact algorithm is configurable and documented in `DOMAIN_MODEL.md`.

---

## 9. AI rules

AI generates:

- explanations
- exercises
- qualitative feedback
- roadmap proposals
- knowledge proposals

Application code controls:

- state
- persistence
- permissions
- filesystem access
- scoring aggregation
- scheduling
- transitions

AI never receives unrestricted filesystem access.

---

## 10. Obsidian rules

The application must:

- preserve user-authored content
- use stable IDs
- use managed sections
- detect conflicts
- generate diffs
- support approval
- use atomic writes

The `.obsidian/` directory is read-only to Learning OS in MVP.

---

## 11. First-run flow

```text
Launch
→ choose vault
→ read-only scan
→ classify folders
→ build index
→ create first goal
→ diagnose
→ propose roadmap
→ start learning
```

No automatic modification during initial scan.

---

## 12. Session flow

```text
load goal
→ load knowledge
→ load mistakes
→ select objective
→ select activity
→ user attempts
→ evaluate
→ create evidence
→ update derived state
→ schedule review
→ propose vault changes
→ continue
```

---

## 13. Adaptive selection

Candidate activities are ranked using:

- importance
- weakness
- prerequisite status
- review urgency
- recurring mistakes
- transfer value

The reason for the next activity should be inspectable in debug mode.

---

## 14. Exercise policy

Every exercise must specify:

```text
type
difficulty
concepts
skills
prerequisites
success criteria
hints
solution
common mistakes
transfer variant
```

No solution is shown before the user's attempt unless the user explicitly requests it.

---

## 15. Evaluation policy

Evaluate:

```text
correctness
reasoning
completeness
independence
transfer
confidence calibration
```

The evaluator identifies misconceptions and recommends the next action.

---

## 16. Knowledge consolidation

After meaningful learning:

```text
Evidence
→ Knowledge update proposal
→ Diff
→ User approval
→ Obsidian update
```

Distill knowledge rather than copying entire conversations.

---

## 17. Review

MVP uses simple spaced repetition.

Future versions may use FSRS.

Reviews prioritize:

```text
weak
+
important
+
forgetting
+
prerequisite
+
recurring mistakes
```

---

## 18. Privacy

Default:

```text
telemetry=false
cloud_sync=false
prompt_logging=false
```

Only selected context is sent to a remote model.

The entire vault must never be transmitted by default.

---

## 19. Definition of done

The MVP is done only when the complete end-to-end test passes:

```text
Create goal
→ import existing knowledge
→ diagnostic
→ 80/20
→ roadmap
→ session
→ exercise
→ answer
→ evaluation
→ evidence
→ mastery
→ mistake
→ review
→ vault diff
→ approval
→ Markdown update
```

All destructive paths must have tests.

---

## 20. User onboarding

The first-run experience configures the user's local learning environment before the first learning goal.

Canonical flow:

```text
WELCOME → VAULT → VAULT_SCAN → AI_PROVIDER → CREDENTIAL → MODEL → VALIDATE → FIRST_GOAL → COMPLETE
```

### Vault

The user selects a local Obsidian vault root. The application validates that it exists and is readable, scans it read-only, reports Markdown files and errors, and never modifies `.obsidian/` or notes automatically during onboarding.

### AI provider

MVP provider registry:

```text
Ollama
OpenAI
Anthropic / Claude
OpenRouter
NVIDIA NIM/API
OpenAI-compatible
```

Provider adapters are explicit. The application does not assume that Anthropic, OpenRouter, NVIDIA and arbitrary OpenAI-compatible services have identical semantics.

Credentials are stored using the OS credential/keyring facility where required. API keys are never persisted in SQLite, Markdown, Git, logs, browser local storage, or API responses.

The user chooses the model explicitly, or from a provider model list when supported. A provider must pass connection/model/capability validation before onboarding completes.

Onboarding state is persisted locally and is resumable after restart. Users can reconfigure vault and provider later.
