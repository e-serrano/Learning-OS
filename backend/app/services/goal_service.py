"""Goal application service -- creates a LearningGoal and its initial
state (docs/TASKS.md T065).

Deliberately has no VaultPort dependency: creating a goal must never
modify the vault automatically (docs/AGENTS.md #3 architectural
boundary). Any Obsidian sync is a separate, explicit step through the
change-proposal pipeline (docs/OBSIDIAN_SCHEMA.md), never implicit here.
"""

from datetime import datetime

from app.domain.entities import LearningGoal
from app.domain.enums import GoalStatus, TargetLevel
from app.domain.ports import ClockPort, GoalRepository, IdGeneratorPort
from app.domain.value_objects import FiveLevelScale


class InvalidGoalError(Exception):
    pass


class GoalNotFoundError(Exception):
    pass


class InvalidGoalTransitionError(Exception):
    pass


class GoalApplicationService:
    def __init__(self, goals: GoalRepository, clock: ClockPort, ids: IdGeneratorPort) -> None:
        self._goals = goals
        self._clock = clock
        self._ids = ids

    def create_goal(
        self,
        title: str,
        target_level: TargetLevel,
        description: str | None = None,
        domain: str | None = None,
        priority: FiveLevelScale = 3,
        deadline: datetime | None = None,
        available_minutes_per_week: int | None = None,
    ) -> LearningGoal:
        """A new goal always starts as `draft` (docs/DOMAIN_MODEL.md #17
        state transitions: `draft -> active -> ...`); no concepts, roadmap,
        or vault note are created here -- those come from the diagnostic
        and roadmap pipeline (T066-T068) and the curator (T080+)."""
        if not title.strip():
            raise InvalidGoalError("title must not be blank")

        now = self._clock.now()
        goal = LearningGoal(
            id=self._ids.new_id("goal"),
            title=title,
            description=description,
            domain=domain,
            target_level=target_level,
            status=GoalStatus.DRAFT,
            priority=priority,
            deadline=deadline,
            available_minutes_per_week=available_minutes_per_week,
            created_at=now,
            updated_at=now,
        )
        self._goals.add(goal)
        return goal

    def get_goal(self, goal_id: str) -> LearningGoal:
        goal = self._goals.get(goal_id)
        if goal is None:
            raise GoalNotFoundError(goal_id)
        return goal

    def list_goals(self) -> list[LearningGoal]:
        return self._goals.list_all()

    def pause_goal(self, goal_id: str) -> LearningGoal:
        """Only `active -> paused` is a valid transition
        (docs/DOMAIN_MODEL.md #17); nothing in the codebase yet moves a
        goal out of `draft` (see this task's TASKS.md note), so pausing a
        still-draft goal correctly raises rather than silently accepting it."""
        goal = self.get_goal(goal_id)
        if goal.status != GoalStatus.ACTIVE:
            raise InvalidGoalTransitionError(f"cannot pause a goal in status '{goal.status}'")
        paused = goal.model_copy(
            update={"status": GoalStatus.PAUSED, "updated_at": self._clock.now()}
        )
        self._goals.update(paused)
        return paused

    def complete_goal(self, goal_id: str) -> LearningGoal:
        """Only `active -> completed` is a valid transition (docs/DOMAIN_MODEL.md #17)."""
        goal = self.get_goal(goal_id)
        if goal.status != GoalStatus.ACTIVE:
            raise InvalidGoalTransitionError(f"cannot complete a goal in status '{goal.status}'")
        completed = goal.model_copy(
            update={"status": GoalStatus.COMPLETED, "updated_at": self._clock.now()}
        )
        self._goals.update(completed)
        return completed
