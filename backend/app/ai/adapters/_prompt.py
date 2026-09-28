import json

from app.ai.prompts import PROMPT_REGISTRY
from app.ai.protocol import AIRequest
from app.config.languages import SUPPORTED_LANGUAGES

_JSON_ONLY_SUFFIX = (
    " Respond only with valid JSON matching the required schema -- no prose, no markdown fences."
)


def _language_directive(request: AIRequest) -> str:
    """Only ever emits one of the fixed sentences below -- never the raw
    `constraints["language"]` value -- so an unrecognized or attacker-
    influenced value degrades to a no-op instead of reaching the system
    prompt verbatim (docs/AGENTS.md #14, docs/AI_CONTRACTS.md #11)."""
    code = request.constraints.get("language")
    name = SUPPORTED_LANGUAGES.get(code) if isinstance(code, str) else None
    if name is None or name == "English":
        return ""
    # Explicit field examples beyond "content" (docs/TASKS.md T151,
    # reported live: an exercise's `prompt` came back in English despite
    # this constraint) -- the original wording only called out Obsidian
    # note content, which a model can reasonably read as not applying to
    # other roles' free-text fields like an exercise prompt or tutor
    # feedback.
    return (
        f" Respond in {name}: every free-text field in your output "
        f"(e.g. `prompt`, `content`, `feedback`, `hints`, `solution`) "
        f"must be written in {name}, not English."
    )


def system_prompt(request: AIRequest) -> str:
    template = PROMPT_REGISTRY.get(request.prompt_version)
    if template is not None:
        base = template.instructions
    else:
        # Unversioned/unknown prompt_version: degrade gracefully rather than fail.
        base = (
            f"You are the {request.role} for Learning OS (prompt version {request.prompt_version})."
        )
    return base + _language_directive(request) + _JSON_ONLY_SUFFIX


def user_prompt(request: AIRequest) -> str:
    return json.dumps(
        {
            "goal": request.goal,
            "current_state": request.current_state,
            "context": request.context,
            "task": request.task,
            "constraints": request.constraints,
        }
    )
