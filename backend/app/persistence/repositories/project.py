import json

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session as DbSession

from app.domain.entities import Project
from app.persistence.models import ProjectConceptModel, ProjectModel
from app.persistence.repositories._util import now_iso


def _to_model(project: Project, created_at: str) -> ProjectModel:
    return ProjectModel(
        id=project.id,
        goal_id=project.goal_id,
        title=project.title,
        objective=project.objective,
        difficulty=project.difficulty,
        status=project.status.value,
        success_criteria_json=json.dumps(project.success_criteria),
        artifact_path=project.artifact_path,
        created_at=created_at,
    )


def _to_entity(model: ProjectModel, concept_ids: list[str]) -> Project:
    return Project(
        id=model.id,
        goal_id=model.goal_id,
        title=model.title,
        objective=model.objective,
        difficulty=model.difficulty,
        status=model.status,  # type: ignore[arg-type]
        concept_ids=concept_ids,
        success_criteria=json.loads(model.success_criteria_json),
        artifact_path=model.artifact_path,
    )


class SqlProjectRepository:
    """Implements app.domain.ports.ProjectRepository against projects
    (T092 gap fix -- see docs/DATABASE_SCHEMA.md).

    concept_ids come from the project_concepts join table, mirroring how
    SqlExerciseRepository handles Exercise.concept_ids. `created_at` is a
    DB-only bookkeeping column not present on the Project domain entity.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _concept_ids(self, db: DbSession, project_id: str) -> list[str]:
        stmt = select(ProjectConceptModel.concept_id).where(
            ProjectConceptModel.project_id == project_id
        )
        return list(db.scalars(stmt))

    def add(self, project: Project) -> None:
        with DbSession(self._engine) as db:
            db.add(_to_model(project, created_at=now_iso()))
            db.flush()  # project row must exist before project_concepts references it
            for concept_id in project.concept_ids:
                db.add(ProjectConceptModel(project_id=project.id, concept_id=concept_id))
            db.commit()

    def get(self, project_id: str) -> Project | None:
        with DbSession(self._engine) as db:
            model = db.get(ProjectModel, project_id)
            if model is None:
                return None
            return _to_entity(model, self._concept_ids(db, project_id))

    def list_by_goal(self, goal_id: str) -> list[Project]:
        with DbSession(self._engine) as db:
            stmt = select(ProjectModel).where(ProjectModel.goal_id == goal_id)
            return [
                _to_entity(model, self._concept_ids(db, model.id)) for model in db.scalars(stmt)
            ]

    def update(self, project: Project) -> None:
        with DbSession(self._engine) as db:
            existing = db.get(ProjectModel, project.id)
            created_at = existing.created_at if existing is not None else now_iso()
            db.merge(_to_model(project, created_at=created_at))
            db.execute(
                delete(ProjectConceptModel).where(ProjectConceptModel.project_id == project.id)
            )
            for concept_id in project.concept_ids:
                db.add(ProjectConceptModel(project_id=project.id, concept_id=concept_id))
            db.commit()
