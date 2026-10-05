import { type FormEvent, useEffect, useState } from 'react'
import {
  type AIProviderConfig,
  ApiError,
  type OnboardingStatus,
  configureAIProvider,
  getStatus,
  listOllamaModels,
  validateAIProvider,
} from '../api/onboarding'
import { useTranslation } from '../i18n/LanguageContext'
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
  const { t } = useTranslation()
  const [phase, setPhase] = useState<Phase>('loading')
  const [error, setError] = useState<string | null>(null)
  const [providerId, setProviderId] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [fallbackModel, setFallbackModel] = useState('')
  const [credential, setCredential] = useState('')
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; reason: string | null } | null>(null)
  // Every provider ever saved, not just the default one -- the backend now
  // keeps one entry (config + keyring ref) per provider so switching away
  // and back never loses it (docs/TASKS.md T162, user request).
  const [saved, setSaved] = useState<AIProviderConfig[]>([])
  // Models the user has pulled into Ollama, fetched through the backend
  // (docs/TASKS.md T163, user request). `null` = not loaded yet or the
  // endpoint is unreachable -- the fields stay free-text in that case.
  const [ollamaModels, setOllamaModels] = useState<string[] | null>(null)
  const [ollamaFailed, setOllamaFailed] = useState(false)

  useEffect(() => {
    getStatus()
      .then((status: OnboardingStatus) => {
        if (status.provider_id) setProviderId(status.provider_id)
        if (status.model) setModel(status.model)
        const current = status.ai_providers.find((p) => p.is_default)
        setSaved(status.ai_providers)
        if (current?.base_url) setBaseUrl(current.base_url)
        // Prefilled from the already-saved config, not the provider's
        // suggested default -- unlike onboarding's first-time setup, a
        // blank field here must mean "no fallback configured", never
        // silently reset an existing one on the next save.
        if (current?.fallback_model) setFallbackModel(current.fallback_model)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
        setPhase('error')
      })
  }, [t])

  useEffect(() => {
    if (phase !== 'ready' || providerId !== 'ollama' || !baseUrl.trim()) return
    let stale = false
    // Debounced: the endpoint field is typed into, one keystroke at a time.
    const timer = setTimeout(() => {
      listOllamaModels(baseUrl.trim())
        .then(({ models }) => {
          if (stale) return
          setOllamaModels(models)
          setOllamaFailed(false)
          // A <select> can only show an installed model: snap a stale value
          // (another provider's, or one since uninstalled) to the first one.
          // Ollama treats `llama3` as `llama3:latest`, so that still matches.
          const installedAs = (name: string) =>
            models.find((m) => m === name || m === `${name}:latest`)
          setModel((current) => installedAs(current) ?? models[0] ?? current)
          setFallbackModel((current) => installedAs(current) ?? '')
        })
        .catch(() => {
          if (stale) return
          setOllamaModels(null)
          setOllamaFailed(true)
        })
    }, 400)
    return () => {
      stale = true
      clearTimeout(timer)
    }
  }, [phase, providerId, baseUrl])

  const provider = PROVIDER_OPTIONS.find((p) => p.id === providerId) ?? null
  const isOllama = providerId === 'ollama'
  const installed = isOllama && ollamaModels && ollamaModels.length > 0 ? ollamaModels : null
  const hasSavedKey = saved.some((p) => p.provider_id === providerId && p.credential_ref !== null)

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
        fallback_model: fallbackModel.trim() || null,
      })
      const validation = await validateAIProvider(credential.trim() || null)
      setResult({ ok: validation.ok, reason: validation.reason })
      if (validation.ok) {
        // Best-effort -- the save already succeeded; a failed refresh only
        // means the "key already saved" hint lags until the next page load.
        getStatus()
          .then((status) => setSaved(status.ai_providers))
          .catch(() => {})
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    } finally {
      setCredential('') // never keep the secret around once it's no longer needed, pass or fail
      setSaving(false)
    }
  }

  if (phase === 'loading') {
    return <p>{t('common.loading')}</p>
  }

  if (phase === 'error') {
    return <div className="message error">{error}</div>
  }

  return (
    <div className="ai-provider-settings">
      <label htmlFor="ai-provider">{t('aiProvider.label')}</label>
      <select
        id="ai-provider"
        value={providerId}
        onChange={(e) => {
          const next = PROVIDER_OPTIONS.find((p) => p.id === e.target.value) ?? null
          const previous = saved.find((p) => p.provider_id === e.target.value)
          setProviderId(e.target.value)
          setBaseUrl(previous?.base_url ?? next?.defaultBaseUrl ?? '')
          setCredential('')
          // Back on a provider saved earlier: restore its own model and
          // fallback instead of leaving the previous provider's in place.
          if (previous) {
            setModel(previous.model)
            setFallbackModel(previous.fallback_model ?? '')
          }
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
            <label htmlFor="ai-base-url">{t('aiProvider.endpointUrl')}</label>
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

        <label htmlFor="ai-model">{t('aiProvider.model')}</label>
        {installed ? (
          <select
            id="ai-model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={saving}
            required
          >
            {installed.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        ) : (
          <input
            id="ai-model"
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={t('aiProvider.modelPlaceholder')}
            disabled={saving}
            required
          />
        )}
        {isOllama && ollamaFailed && <p className="field-hint">{t('aiProvider.ollamaUnreachable')}</p>}
        {isOllama && ollamaModels?.length === 0 && (
          <p className="field-hint">{t('aiProvider.ollamaNoModels')}</p>
        )}
        {provider?.reasoningModelHint && (
          <p className="field-hint">
            {t('aiProvider.reasoningModelHint')} <code>{provider.reasoningModelHint}</code>
          </p>
        )}

        <label htmlFor="ai-fallback-model">{t('aiProvider.fallbackModel')}</label>
        {installed ? (
          <select
            id="ai-fallback-model"
            value={fallbackModel}
            onChange={(e) => setFallbackModel(e.target.value)}
            disabled={saving}
          >
            <option value="">{t('aiProvider.noFallback')}</option>
            {installed.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        ) : (
          <input
            id="ai-fallback-model"
            type="text"
            value={fallbackModel}
            onChange={(e) => setFallbackModel(e.target.value)}
            disabled={saving}
          />
        )}
        <p className="field-hint">
          {t('aiProvider.fallbackModelHint')}
          {provider?.fallbackModelHint && (
            <>
              {' '}
              {t('aiProvider.fallbackModelSuggestion')} <code>{provider.fallbackModelHint}</code>
            </>
          )}
        </p>

        {provider?.requiresApiKey && (
          <>
            <label htmlFor="ai-credential">{t('aiProvider.apiKey')}</label>
            <input
              id="ai-credential"
              type="password"
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              autoComplete="off"
              disabled={saving}
              required={!hasSavedKey}
            />
            <p className="field-hint">
              {hasSavedKey ? t('aiProvider.apiKeySavedHint') : t('aiProvider.apiKeyHint')}
            </p>
          </>
        )}

        <button type="submit" disabled={saving || !providerId || model.trim().length === 0}>
          {saving ? t('aiProvider.testing') : t('aiProvider.saveAndTest')}
        </button>
      </form>

      {result && !result.ok && (
        <div className="message error">
          {t('aiProvider.connectionFailed')} {result.reason}
        </div>
      )}
      {result?.ok && <div className="message success">{t('aiProvider.connectedSuccessfully')}</div>}
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
