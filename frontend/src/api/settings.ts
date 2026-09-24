import { request } from './client'

export interface Settings {
  language: string
  supported_languages: Record<string, string>
  git_auto_commit: boolean
  git_available: boolean
}

export { ApiError } from './client'

export function getSettings(): Promise<Settings> {
  return request('/settings')
}

export function updateLanguage(language: string): Promise<Settings> {
  return request('/settings/language', { method: 'PATCH', body: JSON.stringify({ language }) })
}

export function updateGitAutoCommit(enabled: boolean): Promise<Settings> {
  return request('/settings/git-auto-commit', {
    method: 'PATCH',
    body: JSON.stringify({ enabled }),
  })
}
