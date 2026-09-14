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

Returns validation result and capabilities, never credentials.

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
