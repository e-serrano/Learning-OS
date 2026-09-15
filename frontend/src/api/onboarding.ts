const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export type OnboardingStep =
  | 'WELCOME'
  | 'VAULT'
  | 'VAULT_SCAN'
  | 'AI_PROVIDER'
  | 'CREDENTIAL'
  | 'MODEL'
  | 'VALIDATE'
  | 'FIRST_GOAL'
  | 'COMPLETE'

export interface AIProviderConfig {
  id: string
  provider_id: string
  model: string
  base_url: string | null
  credential_ref: string | null
  enabled: boolean
  is_default: boolean
}

export interface OnboardingStatus {
  onboarding_step: OnboardingStep
  vault_path: string | null
  provider_id: string | null
  model: string | null
  language: string
  ai_providers: AIProviderConfig[]
}

export interface VaultScanResult {
  exists: boolean
  readable: boolean
  markdown_file_count: number
  errors: string[]
}

export interface VaultResponse {
  onboarding_step: OnboardingStep
  scan: VaultScanResult
}

export interface AIProviderResponse {
  onboarding_step: OnboardingStep
}

export interface ValidateResponse {
  onboarding_step: OnboardingStep
  ok: boolean
  reason: string | null
}

export interface CompleteResponse {
  onboarding_step: OnboardingStep
}

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const error = body?.detail?.error
    throw new ApiError(error?.code ?? 'UNKNOWN_ERROR', error?.message ?? response.statusText)
  }

  return response.json() as Promise<T>
}

export function getStatus(): Promise<OnboardingStatus> {
  return request('/onboarding/status')
}

export function configureVault(path: string): Promise<VaultResponse> {
  return request('/onboarding/vault', { method: 'POST', body: JSON.stringify({ path }) })
}

export function configureAIProvider(input: {
  provider_id: string
  model: string
  base_url?: string | null
}): Promise<AIProviderResponse> {
  return request('/onboarding/ai-provider', { method: 'POST', body: JSON.stringify(input) })
}

export function validateAIProvider(credential?: string | null): Promise<ValidateResponse> {
  return request('/onboarding/ai-provider/validate', {
    method: 'POST',
    body: JSON.stringify({ credential: credential ?? null }),
  })
}

export function completeOnboarding(): Promise<CompleteResponse> {
  return request('/onboarding/complete', { method: 'POST' })
}
