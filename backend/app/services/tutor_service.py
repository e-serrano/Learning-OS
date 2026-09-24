"""Interactive tutor turn -- one back-and-forth turn with the Tutor AI
role (docs/TASKS.md T132/T141, docs/AI_CONTRACTS.md #6). `TutorResponse`
and the `tutor.v1` prompt (T017/T058) have existed since early in the AI
contract layer but were never wired into a route until T132 -- every
other AI role (planner, diagnostician, exercise_generator, evaluator,
curator) already had one; tutor was the one gap.

Gated on `SessionMode.SOCRATIC` or `SessionMode.INTERVIEW` (docs/
DOMAIN_MODEL.md's `Session` entity reserved both mode values; SOCRATIC
was wired first by T132, INTERVIEW by T141) -- a tutor turn only makes
sense for a session the caller explicitly started for one of these two
dialogue styles, not as a side channel on an ordinary guided/practice
session. Same contract, same route, same schema for both -- only the
`constraints` steering instruction differs, per docs/AI_CONTRACTS.md #2's
"AI proposes, the application decides" applied to instructional style:
the app biases *how* the model talks, never hardcodes `TutorResponse.mode`
itself, which stays the model's own per-turn judgment either way.

Stateless per turn: the caller resends the conversation-so-far
(`history`) plus their latest `message`; this service persists no
dialogue transcript of its own. A tutor turn produces no `Evidence`
(docs/DOMAIN_MODEL.md #6's `source_type` enum has no tutor/socratic/
interview value) and no mastery update -- it is an interactive scaffold,
not a graded loop, the same distinction `AI_CONTRACTS.md` draws between
the Tutor and Evaluator roles.
"""

from typing import Literal

from pydantic import BaseModel

from app.ai.contracts import TutorResponse
from app.ai.orchestrator import AIOrchestrator
from app.ai.protocol import AIRequest
from app.domain.enums import SessionMode, SessionStatus
from app.domain.ports import GoalRepository, SessionRepository
from app.services.context_builder import ContextBuilder, GoalNotFoundError
from app.services.next_activity_service import InactiveSessionError, SessionNotFoundError

TUTOR_PROMPT_VERSION = "tutor.v1"

SOCRATIC_STYLE_INSTRUCTION = (
    "Use the Socratic method: default to asking one focused question that "
    "leads the learner to the answer themselves, rather than stating it. "
    "Offer a hint only after the learner has attempted an answer and is "
    "still stuck, and give a short explanation only as a last resort."
)

INTERVIEW_STYLE_INSTRUCTION = (
    "Run this as a simulated technical interview, not a teaching session. "
    "Ask one interview-style question at a time, then probe the learner's "
    "answer with a targeted follow-up -- why that approach, what its "
    "complexity or tradeoffs are, how it handles an edge case -- before "
    "moving to the next question. Do not coach, hint, or explain unless "
    "the learner is completely stuck; a real interviewer lets a candidate "
    "reason through difficulty rather than rescuing them. Keep a "
    "professional, neutral interviewer tone throughout."
)

TUTOR_STYLE_INSTRUCTIONS: dict[SessionMode, str] = {
    SessionMode.SOCRATIC: SOCRATIC_STYLE_INSTRUCTION,
    SessionMode.INTERVIEW: INTERVIEW_STYLE_INSTRUCTION,
}


class SessionNotTutorableError(Exception):
    """Raised for any session mode outside `TUTOR_STYLE_INSTRUCTIONS`
    (currently socratic/interview) -- named after the capability, not
    either individual mode, since a third tutor-style mode should extend
    this same check rather than need its own exception type."""


class TutorTurn(BaseModel):
    speaker: Literal["tutor", "learner"]
    content: str


class TutorService:
    def __init__(
        self,
        goals: GoalRepository,
        sessions: SessionRepository,
        context_builder: ContextBuilder,
        orchestrator: AIOrchestrator,
    ) -> None:
        self._goals = goals
        self._sessions = sessions
        self._context_builder = context_builder
        self._orchestrator = orchestrator

    async def ask(
        self,
        session_id: str,
        concept_id: str,
        history: list[TutorTurn],
        message: str = "",
    ) -> TutorResponse:
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        if session.status != SessionStatus.ACTIVE:
            raise InactiveSessionError(session_id)
        style_instruction = TUTOR_STYLE_INSTRUCTIONS.get(session.mode)
        if style_instruction is None:
            raise SessionNotTutorableError(session_id)

        goal = self._goals.get(session.goal_id)
        if goal is None:
            raise GoalNotFoundError(session.goal_id)

        request = AIRequest(
            role="tutor",
            prompt_version=TUTOR_PROMPT_VERSION,
            goal={"id": goal.id, "title": goal.title, "target_level": goal.target_level.value},
            context=self._context_builder.build(session.goal_id, concept_id),
            current_state={"history": [turn.model_dump() for turn in history]},
            task={"concept_id": concept_id, "learner_message": message},
            constraints={"style": session.mode.value, "instructions": style_instruction},
        )
        response = await self._orchestrator.generate(request, TutorResponse, session_id=session_id)
        assert isinstance(response, TutorResponse)
        return response
