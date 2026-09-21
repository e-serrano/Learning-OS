const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export class ApiError extends Error {
  code: string

  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

/** Shared fetch wrapper for every `src/api/*.ts` client -- parses the
 * `{"error": {"code", "message"}}` envelope every backend route returns
 * (docs/API_SPEC.md #11) into an `ApiError` so callers only ever branch
 * on one error type, whichever route they called. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
