import { Navigate, Route, Routes } from 'react-router-dom'
import { AssessmentUI } from '../assessment/AssessmentUI'
import { Dashboard } from '../dashboard/Dashboard'
import { GoalView } from '../goal/GoalView'
import { KnowledgeExplorer } from '../knowledge/KnowledgeExplorer'
import { ProjectView } from '../project/ProjectView'
import { RoadmapView } from '../roadmap/RoadmapView'
import { ReviewsUI } from '../reviews/ReviewsUI'
import { SessionUI } from '../session/SessionUI'
import { AppShell } from './AppShell'
import { Placeholder } from './Placeholder'

/** Route table for the app shell (docs/TASKS.md T109). Each placeholder
 * page here is replaced by its own task: Dashboard (T111, done), Goal
 * view (T112, done), Roadmap view (T113, done), Knowledge explorer
 * (T114, done), Session UI (T115, done), Reviews UI (T116, done),
 * Assessment UI (T117, done), Projects UI (T118, done), Vault diff UI
 * (T119). */
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="goals/:goalId" element={<GoalView />} />
        <Route path="goals/:goalId/roadmap" element={<RoadmapView />} />
        <Route path="goals/:goalId/knowledge" element={<KnowledgeExplorer />} />
        <Route path="sessions/:sessionId" element={<SessionUI />} />
        <Route path="reviews" element={<ReviewsUI />} />
        <Route path="assessments/:assessmentId" element={<AssessmentUI />} />
        <Route path="projects/:projectId" element={<ProjectView />} />
        <Route path="vault" element={<Placeholder title="Vault Changes" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
