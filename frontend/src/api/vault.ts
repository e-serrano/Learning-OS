import { request } from './client'

export type ProposalOperation =
  | 'create_file'
  | 'update_frontmatter'
  | 'replace_managed_section'
  | 'add_link'
export type ProposalStatus = 'pending' | 'approved' | 'rejected' | 'applied' | 'conflicted' | 'failed'

export interface ChangeProposal {
  id: string
  path: string
  operation: ProposalOperation
  section: string | null
  content: string
  status: ProposalStatus
  error: string | null
  created_at: string
  updated_at: string
  applied_at: string | null
}

export interface VaultReindexSummary {
  files_scanned: number
  managed_files: number
  changed_files: number
  errors: string[]
}

export function listVaultChanges(): Promise<{ changes: ChangeProposal[] }> {
  return request('/vault/changes')
}

export function applyVaultChange(changeId: string): Promise<ChangeProposal> {
  return request(`/vault/changes/${changeId}/apply`, { method: 'POST' })
}

export function rejectVaultChange(changeId: string): Promise<ChangeProposal> {
  return request(`/vault/changes/${changeId}/reject`, { method: 'POST' })
}

export function scanVault(): Promise<VaultReindexSummary> {
  return request('/vault/scan', { method: 'POST' })
}
