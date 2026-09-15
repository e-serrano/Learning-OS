import { type FormEvent, useState } from 'react'
import { PROVIDER_OPTIONS } from '../providers'

interface ProviderStepProps {
  onSelected: (providerId: string, baseUrl: string | null) => void
}

export function ProviderStep({ onSelected }: ProviderStepProps) {
  const [providerId, setProviderId] = useState<string | null>(null)
  const [baseUrl, setBaseUrl] = useState('')

  const selected = PROVIDER_OPTIONS.find((p) => p.id === providerId) ?? null

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!selected) return
    onSelected(selected.id, selected.requiresBaseUrl ? baseUrl.trim() : null)
  }

  return (
    <div className="onboarding">
      <h1>Choose an AI provider</h1>
      <p className="subtitle">
        Learning OS never has direct database or filesystem access -- it only proposes content
        through this provider. Local providers keep your data on this machine.
      </p>
      <form onSubmit={handleSubmit}>
        <div className="provider-cards">
          {PROVIDER_OPTIONS.map((option) => (
            <button
              type="button"
              key={option.id}
              className={`provider-card${option.id === providerId ? ' selected' : ''}`}
              onClick={() => {
                setProviderId(option.id)
                setBaseUrl(option.defaultBaseUrl ?? '')
              }}
            >
              <strong>{option.displayName}</strong>
              <div className="tag">
                {option.local ? 'Runs locally' : 'Remote API'}
                {option.requiresApiKey ? ' · requires API key' : ' · no API key required'}
              </div>
            </button>
          ))}
        </div>
        {selected?.requiresBaseUrl && (
          <>
            <label htmlFor="base-url">Endpoint URL</label>
            <input
              id="base-url"
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={selected.defaultBaseUrl ?? 'https://...'}
              required
            />
          </>
        )}
        <button type="submit" disabled={!selected || (selected.requiresBaseUrl && !baseUrl.trim())}>
          Continue
        </button>
      </form>
    </div>
  )
}
