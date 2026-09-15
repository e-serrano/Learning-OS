import { useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  completeOnboarding,
  getStatus,
} from '../../api/onboarding'

interface FinishStepProps {
  alreadyComplete: boolean
  onComplete: (status: OnboardingStatus) => void
}

export function FinishStep({ alreadyComplete, onComplete }: FinishStepProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleComplete() {
    setBusy(true)
    setError(null)
    try {
      await completeOnboarding()
      onComplete(await getStatus())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  if (alreadyComplete) {
    return (
      <div className="onboarding">
        <h1>You're all set</h1>
        <p className="subtitle">
          Vault and AI provider are configured. Learning OS is ready for your first goal.
        </p>
      </div>
    )
  }

  return (
    <div className="onboarding">
      <h1>Ready to go</h1>
      <p className="subtitle">Vault and AI provider are configured and validated.</p>
      <button type="button" onClick={handleComplete} disabled={busy}>
        {busy ? 'Finishing…' : 'Finish setup'}
      </button>
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
