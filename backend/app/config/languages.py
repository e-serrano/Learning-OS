"""Supported content languages (docs/TASKS.md T147, user request: the app
and AI responses restricted to exactly English or Spanish, Spanish
preferred/default).

A closed, curated list rather than a freeform string: the selected value
flows into every AI system prompt as a steering instruction (see
`app/ai/adapters/_prompt.py`), so accepting arbitrary text here would let
uncontrolled content reach the model's system prompt through a config
field -- a prompt-injection surface docs/AGENTS.md #14/#19 rule out.
`AppConfig.language` itself stays a plain `str` (docs/DATABASE_SCHEMA.md
#17 already shipped it that way); this list is enforced at the API
boundary (`app/api/settings.py`), and `_prompt.py` only ever emits one of
these fixed English sentences -- never the stored value verbatim.

Deliberately just two entries (docs/TASKS.md T147 narrowed this down from
an earlier six-language list): the frontend's own translation dictionary
(`frontend/src/i18n/translations.ts`) only ever has `en`/`es` copy, so a
third stored language value would silently fall back to English in the
UI while still being accepted here -- narrower is more honest than wider.
"""

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
}
