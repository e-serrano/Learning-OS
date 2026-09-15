import { type FormEvent, useState } from 'react'
import {
  ApiError,
  type OnboardingStatus,
  type VaultScanResult,
  configureVault,
  getStatus,
} from '../../api/onboarding'

interface VaultStepProps {
  onDone: (status: OnboardingStatus) => void
}

export function VaultStep({ onDone }: VaultStepProps) {
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
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
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
      <h1>Welcome to Learning OS</h1>
      <p className="subtitle">
        Point Learning OS at your Obsidian vault. It only reads it to count Markdown files --
        nothing is modified during this scan.
      </p>
      {!scan && (
        <form onSubmit={handleScan}>
          <label htmlFor="vault-path">Vault folder path</label>
          <input
            id="vault-path"
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/Users/me/Documents/MyVault"
            required
          />
          <button type="submit" disabled={busy || path.trim().length === 0}>
            {busy ? 'Scanning…' : 'Scan vault'}
          </button>
        </form>
      )}
      {scan && (
        <>
          <div className="message success">
            Found {scan.markdown_file_count} Markdown file
            {scan.markdown_file_count === 1 ? '' : 's'} in <code>{path}</code>.
            {scan.errors.length > 0 && ` (${scan.errors.length} read error(s))`}
          </div>
          <button type="button" onClick={handleContinue} disabled={busy}>
            Continue
          </button>
          <button type="button" className="secondary" onClick={() => setScan(null)}>
            Choose a different folder
          </button>
        </>
      )}
      {error && <div className="message error">{error}</div>}
    </div>
  )
}
