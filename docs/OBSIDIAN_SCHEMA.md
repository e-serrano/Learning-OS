# OBSIDIAN_SCHEMA.md

# Learning OS — Obsidian Integration Contract

## 1. Goal

Learning OS integrates with a normal Obsidian vault without taking ownership of it.

The vault remains valid Markdown that can be opened without Learning OS.

---

## 2. Default structure

```text
LearningOS/
├── 00_System/
├── 01_Goals/
├── 02_Roadmaps/
├── 03_Knowledge/
│   ├── Concepts/
│   ├── Skills/
│   ├── Patterns/
│   └── Mistakes/
├── 04_Practice/
│   ├── Exercises/
│   ├── Assessments/
│   └── Projects/
├── 05_Reviews/
├── 06_Resources/
└── 07_Sessions/
```

The root is configurable.

---

## 3. Stable identity

Every managed note must have:

```yaml
id: concept_sql_window_functions
type: concept
```

The `id` is stable even if the filename changes.

---

## 4. Frontmatter

Concept example:

```yaml
---
id: concept_sql_window_functions
type: concept
title: SQL Window Functions
status: usable
mastery: 3.2
confidence: 68
importance: 5
retention: 81
last_practiced: 2026-09-07T12:00:00Z
next_review: 2026-09-10T12:00:00Z
managed_by: learning_os
schema_version: 1
---
```

---

## 5. Managed sections

Learning OS may manage only explicit sections:

```markdown
<!-- LEARNING_OS:BEGIN:SUMMARY -->
Generated summary.
<!-- LEARNING_OS:END:SUMMARY -->
```

```markdown
<!-- LEARNING_OS:BEGIN:MASTERY -->
## Mastery

- Mastery: 3.2/5
- Confidence: 68%
- Retention: 81%
<!-- LEARNING_OS:END:MASTERY -->
```

```markdown
<!-- LEARNING_OS:BEGIN:WEAKNESSES -->
## Current weaknesses

- Choosing the correct window frame.
<!-- LEARNING_OS:END:WEAKNESSES -->
```

User content outside managed sections is never replaced automatically.

---

## 6. Human-authored sections

Recommended:

```markdown
# SQL Window Functions

## My understanding

## My examples

## Questions

## Notes
```

Learning OS should not modify these unless the user explicitly requests it.

---

## 7. Links

Use Obsidian wikilinks:

```markdown
[[GROUP BY]]
[[ROW_NUMBER]]
[[BigQuery Partitioning]]
```

When possible, links should resolve to known managed IDs.

---

## 8. Mistake notes

Example:

```yaml
---
id: mistake_window_frame
type: mistake
concept: concept_sql_window_functions
severity: medium
occurrences: 3
resolved: false
managed_by: learning_os
---
```

---

## 9. Session notes

Example:

```yaml
---
id: session_20260907_001
type: learning_session
goal_id: goal_bigquery
mode: guided
started_at: 2026-09-07T13:00:00Z
---
```

Session notes should contain distilled outcomes, not necessarily the full conversation.

---

## 10. Safe write algorithm

```text
1. Resolve configured vault root.
2. Resolve target path.
3. Read current file.
4. Hash current content.
5. Parse frontmatter.
6. Parse managed sections.
7. Compare with indexed version.
8. If changed externally, abort and reload.
9. Generate patch.
10. Validate patch.
11. Show diff when required.
12. Apply patch atomically.
13. Re-read file.
14. Verify expected managed fields.
15. Update vault index.
```

---

## 11. Atomic writes

Write to a temporary file in the same directory and replace atomically where supported.

Never truncate the original before the new content has been validated.

---

## 12. Conflict detection

If:

```text
current_hash != indexed_hash
```

then the file changed externally.

Do not overwrite.

Surface:

```text
Vault file changed since Learning OS last read it.
Reload and regenerate the proposed change.
```

---

## 13. Initial vault import

First run is read-only.

Process:

```text
scan
→ classify
→ index
→ propose metadata
→ user approval
→ write
```

No automatic content modification during initial scan.

---

## 14. Ignored locations

Support configuration:

```yaml
ignored_paths:
  - .obsidian/
  - Attachments/
  - Templates/
```

The `.obsidian` directory must never be modified by the MVP.

---

## 15. File naming

Default:

```text
Concept Title.md
```

But filenames are not identities.

Handle duplicate filenames by using stable IDs and explicit paths.

---

## 16. Deletion

If a managed file disappears:

- mark it missing
- preserve database evidence
- do not recreate automatically
- offer recovery/recreation

---

## 17. External edits

Learning OS must tolerate:

- Obsidian edits
- plugins modifying files
- Git checkout
- sync tools
- manual edits

Filesystem state always wins over stale cache, subject to conflict protection.
