import { Navigate, Route, Routes } from 'react-router-dom'
import { AssessmentUI } from '../assessment/AssessmentUI'
import { Dashboard } from '../dashboard/Dashboard'
import { GoalView } from '../goal/GoalView'
import { KnowledgeExplorer } from '../knowledge/KnowledgeExplorer'
import { ProjectView } from '../project/ProjectView'
import { RoadmapView } from '../roadmap/RoadmapView'
import { ReviewsUI } from '../reviews/ReviewsUI'
import { SessionUI } from '../session/SessionUI'
import { VaultDiffUI } from '../vault/VaultDiffUI'
import { AppShell } from './AppShell'

/** Route table for the app shell (docs/TASKS.md T109). Phase 11 is
 * complete: Dashboard (T111), Goal view (T112), Roadmap view (T113),
 * Knowledge explorer (T114), Session UI (T115), Reviews UI (T116),
 * Assessment UI (T117), Projects UI (T118), Vault diff UI (T119). */
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
        <Route path="vault" element={<VaultDiffUI />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
