import { type FormEvent, useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  configureAIProvider,
  getStatus,
  validateAIProvider,
} from '../../api/onboarding'
import { useTranslation } from '../../i18n/LanguageContext'
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
  const { t } = useTranslation()
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
        reason: err instanceof ApiError ? err.message : t('common.couldNotReachBackend'),
      })
    } finally {
      setCredential('') // never keep the secret around once it's no longer needed, pass or fail
      setBusy(false)
    }
  }

  return (
    <div className="onboarding">
      <h1>
        {t('onboarding.connectProvider')} {provider?.displayName ?? providerId}
      </h1>
      <p className="subtitle">{t('onboarding.apiKeyIntro')}</p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="model">{t('onboarding.model')}</label>
        <input
          id="model"
          type="text"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder={t('onboarding.modelPlaceholder')}
          required
        />
        {provider?.requiresApiKey && (
          <>
            <label htmlFor="credential">{t('onboarding.apiKey')}</label>
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
          {busy ? t('onboarding.testing') : t('onboarding.testConnection')}
        </button>
        <button type="button" className="secondary" onClick={onBack} disabled={busy}>
          {t('onboarding.back')}
        </button>
      </form>
      {result && !result.ok && (
        <div className="message error">
          {t('onboarding.connectionFailed')} {result.reason}
        </div>
      )}
      {result?.ok && <div className="message success">{t('onboarding.connectedSuccessfully')}</div>}
    </div>
  )
}
