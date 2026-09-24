# API_SPEC.md

# Learning OS — Local API Specification

The API is local-only by default.

Base URL:

```text
http://127.0.0.1:<port>/api/v1
```

## 1. Goals

### Create

`POST /goals`

Request:

```json
{
  "title": "Learn BigQuery",
  "description": "...",
  "target_level": "professional",
  "available_minutes_per_week": 180
}
```

### List

`GET /goals`

### Get

`GET /goals/{goal_id}`

### Pause

`POST /goals/{goal_id}/pause`

### Complete

`POST /goals/{goal_id}/complete`

---

## 2. Vault

### Configure

`POST /vault/configure`

```json
{
  "path": "/path/to/vault"
}
```

### Scan

`POST /vault/scan`

Response:

```json
{
  "files_scanned": 1420,
  "managed_files": 37,
  "changed_files": 4,
  "errors": []
}
```

### Proposed changes

`GET /vault/changes`

### Apply change

`POST /vault/changes/{change_id}/apply`

### Reject change

`POST /vault/changes/{change_id}/reject`

### Search

`GET /vault/search?q=<query>` (docs/TASKS.md T127)

Full-text search over indexed vault Markdown content (SQLite FTS5), kept
current by every `/vault/scan`. `q` must be non-blank (`VALIDATION_ERROR`
otherwise).

Response:

```json
{
  "results": [
    {"path": "Concepts/Window Functions.md", "title": "Window Functions", "snippet": "...uses a [window] function to..."}
  ]
}
```

### Generate embeddings

`POST /vault/embeddings/generate` (docs/TASKS.md T128)

Generates an embedding vector for every currently-indexed vault file whose
content changed since its last embedding (unchanged files are skipped).
Explicit, not automatic on `/vault/scan` -- a real provider's embeddings
call has a cost the caller should trigger deliberately.

Response:

```json
{
  "files_total": 42,
  "embedded": 3,
  "skipped_unchanged": 39,
  "model": "text-embedding-3-small"
}
```

`AI_UNAVAILABLE` if the configured default AI provider has no embeddings
endpoint (Anthropic) or no default embedding model is known for it
(OpenRouter/NVIDIA NIM/OpenAI-compatible -- see
`app/ai/embedding_provider_factory.py`).

### Semantic search

`GET /vault/search/semantic?q=<query>` (docs/TASKS.md T129)

Embedding-similarity search over vault files that already have an
embedding (see "Generate embeddings" above) -- a separate route from
`/search` (lexical FTS): different failure modes and a real per-query
provider cost, unlike FTS. `q` must be non-blank
(`VALIDATION_ERROR`). Returns `[]` if no embeddings have been generated
yet, rather than erroring.

Response:

```json
{
  "results": [
    {"path": "Concepts/Window Functions.md", "title": "Window Functions", "score": 0.87}
  ]
}
```

`score` is cosine similarity between the query and the file's stored
vector. Only compares against vectors from the currently configured
embedding model -- a provider/model change never silently mixes
incomparable vectors into the ranking.

### Clip

`POST /vault/clip` (docs/TASKS.md T135)

The browser extension's only backend entry point. Turns a selection from
any web page into a pending `ChangeProposal` under `Clippings/` -- raw,
unsorted source material, no concept association, distinct from the
Curator AI role's concept-scoped proposals (#9 below). Reviewed and
applied through the same `/vault/changes` pipeline as any other
proposal, never written to the vault directly.

Request:

```json
{
  "url": "https://example.com/window-functions",
  "title": "Window Functions Explained",
  "selection": "A window function computes a value across a set of rows."
}
```

`selection` must be non-blank and under 20,000 characters
(`VALIDATION_ERROR` otherwise). Response is a `ChangeProposal`, same
shape `/vault/changes` returns, `status: "pending"`.

---

## 3. Knowledge

`GET /goals/{goal_id}/knowledge`

Optional filters:

```text
status
mastery_lt
next_review_before
```

### Concept

`GET /concepts/{concept_id}`

### Related concepts

`GET /concepts/{concept_id}/relations`

---

## 4. Roadmap

### Generate

`POST /goals/{goal_id}/roadmap/generate`

### Get

`GET /goals/{goal_id}/roadmap`

### Regenerate

`POST /goals/{goal_id}/roadmap/recalculate`

---

## 5. Diagnostic

`POST /goals/{goal_id}/diagnostic/start`

Returns a diagnostic session.

---

## 6. Sessions

### Start

`POST /goals/{goal_id}/sessions`

```json
{
  "mode": "guided",
  "duration_minutes": 30
}
```

### Get

`GET /sessions/{session_id}`

### Next activity

`POST /sessions/{session_id}/next`

Response:

```json
{
  "activity_id": "activity_...",
  "type": "exercise",
  "content": {}
}
```

### Submit answer

`POST /sessions/{session_id}/activities/{activity_id}/answer`

```json
{
  "answer": "...",
  "confidence": 72
}
```

Response:

```json
{
  "evaluation": {},
  "knowledge_updates": [],
  "next_activity": {}
}
```

### Complete

`POST /sessions/{session_id}/complete`

### Tutor turn (Socratic or interview mode)

`POST /sessions/{session_id}/tutor` (docs/TASKS.md T132, T141)

One stateless interactive turn with the Tutor AI role (docs/AI_CONTRACTS.md
#6). Only usable on a session created with `"mode": "socratic"` or
`"mode": "interview"` -- `SESSION_STATE_ERROR` otherwise (same code as an
inactive session). Same request/response shape for both modes; only the
instructional style the app asks the model for differs (Socratic
questioning vs. a simulated technical interview with probing follow-ups).
The caller resends the conversation-so-far each call; nothing here
persists a transcript, and a tutor turn never creates `Evidence` or
updates mastery -- it is an interactive scaffold, not a graded activity.

Request:

```json
{
  "concept_id": "concept_...",
  "message": "Is it like a subquery?",
  "history": [
    {"speaker": "tutor", "content": "What have you tried so far?"},
    {"speaker": "learner", "content": "Not sure where to start."}
  ]
}
```

`message` and `history` are both optional (default `""` / `[]`) -- the
opening turn of a dialogue has neither.

Response:

```json
{
  "mode": "question",
  "content": "...",
  "check_for_understanding": "...",
  "next_activity": "..."
}
```

`mode` is one of `explain|question|hint|feedback|reflection` (the model's
own choice per turn, biased toward `question` by the request's
`constraints`, never hardcoded by the application).

---

## 7. Reviews

`GET /reviews/today`

`POST /reviews/{review_id}/complete`

Request:

```json
{
  "answer": "...",
  "confidence": 65
}
```

---

## 8. Assessments

`POST /goals/{goal_id}/assessments`

`GET /assessments/{assessment_id}`

`POST /assessments/{assessment_id}/answer`

`POST /assessments/{assessment_id}/complete`

### Teach-back (docs/TASKS.md T133)

`POST /goals/{goal_id}/teach-back`

```json
{"concept_id": "concept_..."}
```

Generates a teach-back prompt for the concept -- asks the learner to
explain it in their own words rather than solve a normal exercise -- and
scaffolds a `mode="teach_back"` Session + Activity to hold it, the same
shape `POST /goals/{goal_id}/assessments` uses for transfer assessments.
Response mirrors the assessment response (`teach_back_id` instead of
`assessment_id`), `exercise.type` is always `"teach_back"`.

`GET /teach-back/{teach_back_id}`

Unlike assessments, answering and completing reuse the ordinary session
routes unchanged -- `POST /sessions/{session_id}/activities/{activity_id}/answer`
(`teach_back_id` *is* the `activity_id`) and
`POST /sessions/{session_id}/complete`. A teach-back answer is graded by
the same Evaluator as any exercise; the only difference is that the
resulting Evidence is recorded with `source_type: "teach_back"` instead
of `"exercise"`, so progress/retrieval can distinguish it later.

---

## 9. Projects

`POST /goals/{goal_id}/projects`

`GET /goals/{goal_id}/projects`

`GET /projects/{project_id}`

`POST /projects/{project_id}/tasks/{task_id}/submit`

---

## 10. Progress

`GET /goals/{goal_id}/progress`

Response:

```json
{
  "mastery": 0.62,
  "concepts_total": 42,
  "mastered": 12,
  "weak": 8,
  "due_reviews": 5,
  "recent_sessions": 7
}
```

---

## 11. Errors

Use standard HTTP semantics.

Error envelope:

```json
{
  "error": {
    "code": "VAULT_CONFLICT",
    "message": "The file changed externally.",
    "details": {}
  }
}
```

Known codes:

```text
VALIDATION_ERROR
NOT_FOUND
CONFLICT
VAULT_UNAVAILABLE
VAULT_CONFLICT
AI_UNAVAILABLE
AI_INVALID_OUTPUT
SESSION_STATE_ERROR
PERMISSION_DENIED
```

---

## 12. Local security

Bind to loopback by default:

```text
127.0.0.1
```

Do not expose externally unless explicitly configured.

Future authentication is required before supporting non-local binding.

---

## 13. Onboarding

`GET /onboarding/status`

`POST /onboarding/vault`

```json
{"path":"/path/to/vault"}
```

`POST /onboarding/ai-provider`

```json
{"provider_id":"openrouter","model":"provider/model","base_url":null}
```

`POST /onboarding/ai-provider/validate`

```json
{"credential": "sk-..."}
```

`credential` is optional (omit for providers that don't require one, e.g.
`mock`). Validates in two stages (docs/TASKS.md T145): structural first
(required fields present), then — only if that passes — one real minimal
request through the actual provider, so `ok: true` means the provider
genuinely answered, not just that the form was filled in correctly. `mock`
skips the live stage (deterministic/offline by design). The raw credential
value is never echoed back or persisted — on success it is stored via the
OS keyring and only a `credential_ref` is kept. Returns validation result
and capabilities, never credentials:

```json
{"onboarding_step": "VALIDATE", "ok": true, "reason": null}
```

`POST /onboarding/complete`

Requires a valid vault and successfully validated AI provider.

## 14. Provider configuration

Supported IDs:

```text
ollama
openai
anthropic
openrouter
nvidia_nim
openai_compatible
mock
```

Configuration endpoints must never return API keys. The frontend must not persist provider credentials in browser storage.

## 15. Settings

`GET /settings`

```json
{"language": "en", "supported_languages": {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "pt": "Portuguese", "it": "Italian"}, "git_auto_commit": false, "git_available": true}
```

`PATCH /settings/language`

```json
{"language": "es"}
```

Rejects a code outside `supported_languages` with `VALIDATION_ERROR` (400). The stored value is a general app preference, not onboarding-gated — it can be changed at any time, before or after `/onboarding/complete`. Every AI request the app makes is steered by the configured language: `AIOrchestrator.generate` injects `constraints.language` into the common request envelope (docs/AI_CONTRACTS.md #2) for every role, which covers AI-generated Obsidian note content (the curator, docs/AI_CONTRACTS.md #9) as well as tutor/exercise/evaluator output.

`PATCH /settings/git-auto-commit`

```json
{"enabled": true}
```

Opt-in (docs/TASKS.md T138, docs/AGENTS.md #22: "Automatic commits are opt-in"): once on, every vault write `ApplyChangeService` applies is also committed to the vault's own git history, one commit per file, never a bulk/whole-tree commit. `git_available` in the `GET`/`PATCH` response is read-only and informational — whether the *currently configured* vault is already a git repository, independent of whether the setting is on; the frontend uses it to disable the checkbox rather than let the user turn on a setting that can't do anything yet. Enabling it against a non-git vault is harmless — every commit attempt is simply a no-op (docs/AGENTS.md #22: never resets, force-pushes, or touches unrelated dirty changes; this integration never pushes to a remote at all).

## 16. Sandbox

`POST /sandbox/sql`

```json
{"sql": "CREATE TABLE t (id INTEGER); INSERT INTO t VALUES (1); SELECT * FROM t;"}
```

```json
{"columns": ["id"], "rows": [[1]], "row_count": 1, "truncated": false, "statement_count": 3, "error": null}
```

A "try it" console (docs/TASKS.md T137): runs the caller's own SQL against a fresh, throwaway in-memory SQLite database, scoped to this one request only. Purely informational — never persisted, never linked to a concept/exercise/evidence, never influences evaluation or mastery. Blank or oversized SQL (over 20,000 characters, or over 50 statements) is a 400 `VALIDATION_ERROR`; a SQL error from the query itself (bad syntax, unknown table, `ATTACH DATABASE` — always denied) is a normal 200 response with `error` set, the same way a wrong quiz answer is not an HTTP error. Long-running queries are interrupted after 5 seconds; result sets are capped at 200 rows (`truncated: true` past that).
