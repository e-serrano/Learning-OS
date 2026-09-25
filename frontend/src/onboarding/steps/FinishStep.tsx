import { useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  completeOnboarding,
  getStatus,
} from '../../api/onboarding'
import { useTranslation } from '../../i18n/LanguageContext'

interface FinishStepProps {
  alreadyComplete: boolean
  onComplete: (status: OnboardingStatus) => void
}

export function FinishStep({ alreadyComplete, onComplete }: FinishStepProps) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleComplete() {
    setBusy(true)
    setError(null)
    try {
      await completeOnboarding()
      onComplete(await getStatus())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    } finally {
      setBusy(false)
    }
  }

  if (alreadyComplete) {
    return (
      <div className="onboarding">
        <h1>{t('onboarding.allSet')}</h1>
        <p className="subtitle">{t('onboarding.allSetSubtitle')}</p>
      </div>
    )
  }

  return (
    <div className="onboarding">
      <h1>{t('onboarding.readyToGo')}</h1>
      <p className="subtitle">{t('onboarding.readySubtitle')}</p>
      <button type="button" onClick={handleComplete} disabled={busy}>
        {busy ? t('onboarding.finishing') : t('onboarding.finishSetup')}
      </button>
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
