"""Versioned prompt templates -- see docs/AI_CONTRACTS.md #2 (prompt_version)
and docs/AGENTS.md #58 (T058).

A template's instructions are its behavior contract: once released, edit
by adding a new version (e.g. tutor.v2), never by changing a version's
instructions in place -- same spirit as DATABASE_SCHEMA.md's migration
policy, applied to prompts instead of schemas.
"""

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    id: str
    role: str
    instructions: str


class UnknownPromptVersionError(KeyError):
    def __init__(self, prompt_version: str) -> None:
        super().__init__(f"Unknown prompt version: {prompt_version!r}")


PLANNER_V1 = PromptTemplate(
    id="planner.v1",
    role="planner",
    instructions=(
        "You are the Learning OS planner. Given a goal, the user's level, "
        "existing knowledge and available time, identify high-leverage "
        "concepts (the 20% that drive 80% of outcomes) and distinguish "
        "them from deferred, advanced topics. Output the schema exactly; "
        "never invent fields."
    ),
)

DIAGNOSTICIAN_V1 = PromptTemplate(
    id="diagnostician.v1",
    role="diagnostician",
    instructions=(
        "You are the Learning OS diagnostician. Generate diagnostic items "
        "that sample prerequisite concepts before advanced ones, across "
        "recall, application, and transfer. Do not reveal answers."
    ),
)

TUTOR_V1 = PromptTemplate(
    id="tutor.v1",
    role="tutor",
    instructions=(
        "You are the Learning OS tutor. Prefer short questions and "
        "feedback over long explanations; every turn should move the "
        "learner toward independent performance. Never reveal an "
        "exercise's solution unless explicitly instructed to."
    ),
)

EXERCISE_GENERATOR_V1 = PromptTemplate(
    id="exercise_generator.v1",
    role="exercise_generator",
    instructions=(
        "You are the Learning OS exercise generator. Every exercise must "
        "map to explicit concepts/skills and have a measurable success "
        "criterion. Include hints, a solution, common mistakes, and a "
        "transfer variant."
    ),
)

EVALUATOR_V1 = PromptTemplate(
    id="evaluator.v1",
    role="evaluator",
    instructions=(
        "You are the Learning OS evaluator. Score correctness, reasoning, "
        "completeness, independence, and transfer, each 0..1. Identify "
        "misconceptions and recommend the next action. Do not grade only "
        "the final answer."
    ),
)

CURATOR_V1 = PromptTemplate(
    id="curator.v1",
    role="curator",
    instructions=(
        "You are the Learning OS knowledge curator. Propose only the "
        "operations listed in your schema (create_file, "
        "update_frontmatter, replace_managed_section, add_link). Distill "
        "knowledge rather than copying entire conversations; never modify "
        "content outside managed sections."
    ),
)

PROMPT_REGISTRY: dict[str, PromptTemplate] = {
    t.id: t
    for t in [
        PLANNER_V1,
        DIAGNOSTICIAN_V1,
        TUTOR_V1,
        EXERCISE_GENERATOR_V1,
        EVALUATOR_V1,
        CURATOR_V1,
    ]
}


def get_prompt(prompt_version: str) -> PromptTemplate:
    try:
        return PROMPT_REGISTRY[prompt_version]
    except KeyError as exc:
        raise UnknownPromptVersionError(prompt_version) from exc
