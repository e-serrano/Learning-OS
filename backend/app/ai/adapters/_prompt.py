import json

from app.ai.protocol import AIRequest


def system_prompt(request: AIRequest) -> str:
    return (
        f"You are the {request.role} for Learning OS (prompt version "
        f"{request.prompt_version}). Respond only with valid JSON matching "
        f"the required schema -- no prose, no markdown fences."
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
