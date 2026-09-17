"""Diagnostic session -- turns AI-proposed diagnostic items into a real
Session + Activities (docs/TASKS.md T102, docs/API_SPEC.md #5:
`POST /goals/{id}/diagnostic/start`).

T066's own note already flagged this gap: `DiagnosticService.record_response`
requires a real `activity_id`, "assumes a Session (`mode=assessment`) +
Activity already exist, created by the flow that invokes the
diagnostic" -- this is that flow. `concept_ids` are not a request
parameter (API_SPEC.md #5 documents no request body) -- every concept
currently linked to the goal is diagnosed, which only makes sense once
a roadmap (T101) has populated them.

The question text is never persisted on `Activity` (no free-text field,
same gap as T093/T094's project tasks) nor anywhere else before it is
answered -- it is returned once here and only re-surfaces in
`Evidence.metadata` after `record_response` grades it, exactly the
existing precedent for diagnostic/review answers (T066, T087).
"""

from dataclasses import dataclass
from typing import Literal

from app.domain.entities import Activity, Session
from app.domain.enums import ActivityStatus, ActivityType, SessionMode, SessionStatus
from app.domain.ports import (
    ActivityRepository,
    ClockPort,
    ConceptRepository,
    GoalRepository,
    IdGeneratorPort,
    SessionRepository,
)
from app.services.context_builder import GoalNotFoundError
from app.services.diagnostic_service import DiagnosticService


class NoConceptsForGoalError(Exception):
    pass


@dataclass(frozen=True)
class DiagnosticSessionItem:
    activity_id: str
    concept_id: str
    evidence_type: Literal["recall", "application", "transfer"]
    question: str
    difficulty: int


@dataclass(frozen=True)
class DiagnosticSessionResult:
    session: Session
    items: list[DiagnosticSessionItem]


class DiagnosticSessionService:
    def __init__(
        self,
        goals: GoalRepository,
        concepts: ConceptRepository,
        sessions: SessionRepository,
        activities: ActivityRepository,
        diagnostic: DiagnosticService,
        clock: ClockPort,
        ids: IdGeneratorPort,
    ) -> None:
        self._goals = goals
        self._concepts = concepts
        self._sessions = sessions
        self._activities = activities
        self._diagnostic = diagnostic
        self._clock = clock
        self._ids = ids

    async def start_diagnostic(self, goal_id: str) -> DiagnosticSessionResult:
        if self._goals.get(goal_id) is None:
            raise GoalNotFoundError(goal_id)

        concept_ids = [c.id for c in self._concepts.list_by_goal(goal_id)]
        if not concept_ids:
            raise NoConceptsForGoalError(goal_id)

        diagnostic_items = await self._diagnostic.generate_items(goal_id, concept_ids)

        session = Session(
            id=self._ids.new_id("session"),
            goal_id=goal_id,
            mode=SessionMode.ASSESSMENT,
            objective="Diagnostic assessment",
            status=SessionStatus.ACTIVE,
            started_at=self._clock.now(),
        )
        self._sessions.add(session)

        items: list[DiagnosticSessionItem] = []
        for sequence, item in enumerate(diagnostic_items, start=1):
            activity = Activity(
                id=self._ids.new_id("activity"),
                session_id=session.id,
                type=ActivityType.ASSESSMENT,
                sequence=sequence,
                concept_ids=[item.concept_id],
                status=ActivityStatus.PENDING,
            )
            self._activities.add(activity)
            items.append(
                DiagnosticSessionItem(
                    activity_id=activity.id,
                    concept_id=item.concept_id,
                    evidence_type=item.evidence_type,
                    question=item.question,
                    difficulty=item.difficulty,
                )
            )

        return DiagnosticSessionResult(session=session, items=items)
