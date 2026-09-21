import { request } from './client'

export interface Project {
  id: string
  goal_id: string
  title: string
  objective: string
  difficulty: number
  status: string
  concept_ids: string[]
  success_criteria: string[]
  artifact_path: string | null
}

export interface ProjectTask {
  task_id: string
  sequence: number
  description: string
  status: string
}

export interface CreateProjectResult {
  project: Project
  session_id: string
  tasks: ProjectTask[]
}

export interface SubmitTaskEvaluation {
  correctness: number
  reasoning: number
  independence: number
  transfer: number
  feedback: string
  misconceptions: string[]
}

export interface SubmitTaskConceptUpdate {
  concept_id: string
  mastery: number
  status: string
}

export interface SubmitTaskResult {
  task_id: string
  task_status: string
  evaluation: SubmitTaskEvaluation | null
  updated_concepts: SubmitTaskConceptUpdate[]
}

export function createProject(goalId: string, conceptIds: string[]): Promise<CreateProjectResult> {
  return request(`/goals/${goalId}/projects`, {
    method: 'POST',
    body: JSON.stringify({ concept_ids: conceptIds }),
  })
}

export function listProjects(goalId: string): Promise<{ projects: Project[] }> {
  return request(`/goals/${goalId}/projects`)
}

export function getProject(projectId: string): Promise<Project> {
  return request(`/projects/${projectId}`)
}

export function submitTask(
  projectId: string,
  taskId: string,
  deliverable: string,
): Promise<SubmitTaskResult> {
  return request(`/projects/${projectId}/tasks/${taskId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ deliverable }),
  })
}
