import json

from app.ai.prompts import PROMPT_REGISTRY
from app.ai.protocol import AIRequest

_JSON_ONLY_SUFFIX = (
    " Respond only with valid JSON matching the required schema -- no "
    "prose, no markdown fences."
)


def system_prompt(request: AIRequest) -> str:
    template = PROMPT_REGISTRY.get(request.prompt_version)
    if template is not None:
        return template.instructions + _JSON_ONLY_SUFFIX
    # Unversioned/unknown prompt_version: degrade gracefully rather than fail.
    return (
        f"You are the {request.role} for Learning OS (prompt version "
        f"{request.prompt_version})." + _JSON_ONLY_SUFFIX
    )


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
