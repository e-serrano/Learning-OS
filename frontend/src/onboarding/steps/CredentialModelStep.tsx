import { type FormEvent, useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  configureAIProvider,
  getStatus,
  validateAIProvider,
} from '../../api/onboarding'
import { PROVIDER_OPTIONS } from '../providers'

interface CredentialModelStepProps {
  providerId: string
  baseUrl: string | null
  onValidated: (status: OnboardingStatus) => void
  onBack: () => void
}

export function CredentialModelStep({
  providerId,
  baseUrl,
  onValidated,
  onBack,
}: CredentialModelStepProps) {
  const provider = PROVIDER_OPTIONS.find((p) => p.id === providerId)
  const [model, setModel] = useState('')
  const [credential, setCredential] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; reason: string | null } | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      await configureAIProvider({ provider_id: providerId, model: model.trim(), base_url: baseUrl })
      const validation = await validateAIProvider(credential.trim() || null)
      setResult({ ok: validation.ok, reason: validation.reason })
      if (validation.ok) {
        onValidated(await getStatus())
      }
    } catch (err) {
      setResult({
        ok: false,
        reason: err instanceof ApiError ? err.message : 'Could not reach the backend',
      })
    } finally {
      setCredential('') // never keep the secret around once it's no longer needed, pass or fail
      setBusy(false)
    }
  }

  return (
    <div className="onboarding">
      <h1>Connect {provider?.displayName ?? providerId}</h1>
      <p className="subtitle">
        The API key is sent once to store it in your OS keyring, then discarded -- it is never
        saved in this browser or in Learning OS's database.
      </p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="model">Model</label>
        <input
          id="model"
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="e.g. gpt-5, claude-opus-5, llama3"
          required
        />
        {provider?.requiresApiKey && (
          <>
            <label htmlFor="credential">API key</label>
            <input
              id="credential"
              type="password"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              autoComplete="off"
              required
            />
          </>
        )}
        <button type="submit" disabled={busy || model.trim().length === 0}>
          {busy ? 'Testing…' : 'Test connection'}
        </button>
        <button type="button" className="secondary" onClick={onBack} disabled={busy}>
          Back
        </button>
      </form>
      {result && !result.ok && (
        <div className="message error">Connection failed: {result.reason}</div>
      )}
      {result?.ok && <div className="message success">Connected successfully.</div>}
    </div>
  )
}
