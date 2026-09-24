import { type FormEvent, useEffect, useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  configureAIProvider,
  getStatus,
  validateAIProvider,
} from '../api/onboarding'
import { PROVIDER_OPTIONS } from '../onboarding/providers'

type Phase = 'loading' | 'error' | 'ready'

/** AI provider section of Settings (docs/TASKS.md T146, user request):
 * onboarding (`OnboardingWizard`) only ever runs once, before
 * `App.tsx` swaps into the routed app shell for good -- there was no way
 * back into it to switch provider, model or API key afterward. Reuses
 * the exact same two backend calls the onboarding wizard's own
 * `ProviderStep`/`CredentialModelStep` already make
 * (`POST /onboarding/ai-provider` then `/ai-provider/validate`, which
 * `docs/API_SPEC.md` #13 documents as callable at any time, not gated
 * to the onboarding flow) -- no new backend route needed. */
export function AIProviderSettings() {
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [providerId, setProviderId] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [credential, setCredential] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; reason: string | null } | null>(null)

  useEffect(() => {
    getStatus()
      .then((status: OnboardingStatus) => {
        if (status.provider_id) setProviderId(status.provider_id)
        if (status.model) setModel(status.model)
        const current = status.ai_providers.find((p) => p.is_default)
        if (current?.base_url) setBaseUrl(current.base_url)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
        setPhase('error')
      })
  }, [])

  const provider = PROVIDER_OPTIONS.find((p) => p.id === providerId) ?? null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setResult(null)
    setError(null)
    try {
      await configureAIProvider({
        provider_id: providerId,
        model: model.trim(),
        base_url: provider?.requiresBaseUrl ? baseUrl.trim() : null,
      })
      const validation = await validateAIProvider(credential.trim() || null)
      setResult({ ok: validation.ok, reason: validation.reason })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setCredential('') // never keep the secret around once it's no longer needed, pass or fail
      setSaving(false)
    }
  }

  if (phase === 'loading') {
    return <p>Loading…</p>
  }

  if (phase === 'error') {
    return <div className="message error">{error}</div>
  }

  return (
    <div className="ai-provider-settings">
      <label htmlFor="ai-provider">AI provider</label>
      <select
        id="ai-provider"
        value={providerId}
        onChange={(e) => {
          const next = PROVIDER_OPTIONS.find((p) => p.id === e.target.value) ?? null
          setProviderId(e.target.value)
          setBaseUrl(next?.defaultBaseUrl ?? '')
        }}
        disabled={saving}
      >
        {PROVIDER_OPTIONS.map((option) => (
          <option key={option.id} value={option.id}>
            {option.displayName}
          </option>
        ))}
      </select>

      <form onSubmit={handleSubmit}>
        {provider?.requiresBaseUrl && (
          <>
            <label htmlFor="ai-base-url">Endpoint URL</label>
            <input
              id="ai-base-url"
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={provider.defaultBaseUrl ?? 'https://...'}
              disabled={saving}
              required
            />
          </>
        )}

        <label htmlFor="ai-model">Model</label>
        <input
          id="ai-model"
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="e.g. gpt-5, claude-sonnet-5, llama3"
          disabled={saving}
          required
        />

        {provider?.requiresApiKey && (
          <>
            <label htmlFor="ai-credential">API key</label>
            <input
              id="ai-credential"
              type="password"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              autoComplete="off"
              disabled={saving}
              required
            />
            <p className="field-hint">
              Re-enter your key every time you save here, even just to change the model -- it is
              never stored in the browser or database, only sent once to the OS keyring (or the
              encrypted equivalent in Docker).
            </p>
          </>
        )}

        <button type="submit" disabled={saving || !providerId || model.trim().length === 0}>
          {saving ? 'Testing…' : 'Save & test connection'}
        </button>
      </form>

      {result && !result.ok && (
        <div className="message error">Connection failed: {result.reason}</div>
      )}
      {result?.ok && <div className="message success">Connected successfully.</div>}
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
