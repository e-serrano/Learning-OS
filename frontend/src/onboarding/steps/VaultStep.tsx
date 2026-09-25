import { type FormEvent, useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  type VaultScanResult,
  configureVault,
  getStatus,
} from '../../api/onboarding'
import { useTranslation } from '../../i18n/LanguageContext'

interface VaultStepProps {
  onDone: (status: OnboardingStatus) => void
}

export function VaultStep({ onDone }: VaultStepProps) {
  const { t } = useTranslation()
  const [path, setPath] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scan, setScan] = useState<VaultScanResult | null>(null)

  async function handleScan(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = await configureVault(path.trim())
      setScan(result.scan)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('common.couldNotReachBackend'))
    } finally {
      setBusy(false)
    }
  }

  async function handleContinue() {
    setBusy(true)
    try {
      onDone(await getStatus())
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="onboarding">
      <h1>{t('onboarding.welcome')}</h1>
      <p className="subtitle">{t('onboarding.vaultIntro')}</p>
      {!scan && (
        <form onSubmit={handleScan}>
          <label htmlFor="vault-path">{t('onboarding.vaultPathLabel')}</label>
          <input
            id="vault-path"
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/Users/me/Documents/MyVault"
            required
          />
          <button type="submit" disabled={busy || path.trim().length === 0}>
            {busy ? t('onboarding.scanning') : t('onboarding.scanVault')}
          </button>
        </form>
      )}
      {scan && (
        <>
          <div className="message success">
            {t(
              scan.markdown_file_count === 1
                ? 'onboarding.foundMarkdownFile'
                : 'onboarding.foundMarkdownFilePlural',
            )}{' '}
            {scan.markdown_file_count}{' '}
            {t(scan.markdown_file_count === 1 ? 'onboarding.markdownFile' : 'onboarding.markdownFiles')}{' '}
            {t('onboarding.in')} <code>{path}</code>.
            {scan.errors.length > 0 && ` (${scan.errors.length} ${t('onboarding.readErrors')})`}
          </div>
          <button type="button" onClick={handleContinue} disabled={busy}>
            {t('onboarding.continue')}
          </button>
          <button type="button" className="secondary" onClick={() => setScan(null)}>
            {t('onboarding.chooseDifferentFolder')}
          </button>
        </>
      )}
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
