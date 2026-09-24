import { request } from './client'

export interface Settings {
  language: string
  supported_languages: Record<string, string>
}

export { ApiError } from './client'

export function getSettings(): Promise<Settings> {
  return request('/settings')
}

export function updateLanguage(language: string): Promise<Settings> {
  return request('/settings/language', { method: 'PATCH', body: JSON.stringify({ language }) })
}
