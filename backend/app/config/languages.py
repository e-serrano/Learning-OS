"""Supported content languages (docs/TASKS.md, user request: a language
preference for the app and for AI-written Obsidian notes).

A closed, curated list rather than a freeform string: the selected value
flows into every AI system prompt as a steering instruction (see
`app/ai/adapters/_prompt.py`), so accepting arbitrary text here would let
uncontrolled content reach the model's system prompt through a config
field -- a prompt-injection surface docs/AGENTS.md #14/#19 rule out.
`AppConfig.language` itself stays a plain `str` (docs/DATABASE_SCHEMA.md
#17 already shipped it that way); this list is enforced at the API
boundary (`app/api/settings.py`), and `_prompt.py` only ever emits one of
these fixed English sentences -- never the stored value verbatim.
"""

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "it": "Italian",
}
