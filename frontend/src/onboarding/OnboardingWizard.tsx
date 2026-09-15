import { useEffect, useState } from 'react'
import { ApiError, type OnboardingStatus, getStatus } from '../api/onboarding'
import './onboarding.css'
import { CredentialModelStep } from './steps/CredentialModelStep'
import { FinishStep } from './steps/FinishStep'
import { ProviderStep } from './steps/ProviderStep'
import { VaultStep } from './steps/VaultStep'

export function OnboardingWizard() {
  const [status, setStatus] = useState<OnboardingStatus | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [pendingProvider, setPendingProvider] = useState<{
    providerId: string
    baseUrl: string | null
  } | null>(null)

  useEffect(() => {
    getStatus()
      .then(setStatus)
      .catch((err: unknown) =>
        setLoadError(err instanceof ApiError ? err.message : 'Could not reach the backend'),
      )
  }, [])

  if (loadError) {
    return (
      <div className="onboarding">
        <h1>Learning OS</h1>
        <div className="message error">{loadError}</div>
      </div>
    )
  }
  if (!status) {
    return (
      <div className="onboarding">
        <p>Loading…</p>
      </div>
    )
  }

  if (status.onboarding_step === 'COMPLETE') {
    return <FinishStep alreadyComplete onComplete={setStatus} />
  }

  if (status.onboarding_step === 'VALIDATE') {
    return <FinishStep alreadyComplete={false} onComplete={setStatus} />
  }

  if (
    pendingProvider &&
    (status.onboarding_step === 'VAULT_SCAN' || status.onboarding_step === 'AI_PROVIDER')
  ) {
    return (
      <CredentialModelStep
        providerId={pendingProvider.providerId}
        baseUrl={pendingProvider.baseUrl}
        onValidated={setStatus}
        onBack={() => setPendingProvider(null)}
      />
    )
  }

  if (status.onboarding_step === 'VAULT_SCAN' || status.onboarding_step === 'AI_PROVIDER') {
    return (
      <ProviderStep
        onSelected={(providerId, baseUrl) => setPendingProvider({ providerId, baseUrl })}
      />
    )
  }

  return <VaultStep onDone={setStatus} />
}
