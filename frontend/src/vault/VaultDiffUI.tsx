import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import {
  type ChangeProposal,
  applyVaultChange,
  listVaultChanges,
  rejectVaultChange,
  scanVault,
} from '../api/vault'
import './vault.css'

/** Vault diff UI (docs/TASKS.md T119, dep T097): before/after +
 * approve/reject for pending Obsidian writes. `ChangeProposal` (T044)
 * has no "before" field, and no route anywhere in the API reads a raw
 * note's current content (the vault is otherwise read-only from the
 * frontend's perspective) -- so "before" is shown as an honest
 * placeholder rather than fabricated, same "say what the data actually
 * supports" choice T118 made for its own real gap. "Approve" is
 * `/apply`, which already chains approve+apply in one call (T097's own
 * docstring: there is no separate `/approve` route); a conflict or
 * failure comes back as 200 with the proposal marked
 * `conflicted`/`failed` (T097), not an HTTP error, so this reads
 * `result.status` after the call rather than relying on a thrown
 * `ApiError` to detect it. */
export function VaultDiffUI() {
  const [changes, setChanges] = useState<ChangeProposal[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanSummary, setScanSummary] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const { changes: list } = await listVaultChanges()
      setChanges(list)
      setError(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleScan() {
    setScanning(true)
    setError(null)
    try {
      const summary = await scanVault()
      setScanSummary(
        `Scanned ${summary.files_scanned} files -- ${summary.changed_files} changed, ${summary.errors.length} error(s).`,
      )
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setScanning(false)
    }
  }

  function updateChange(updated: ChangeProposal) {
    setChanges((prev) => prev?.map((c) => (c.id === updated.id ? updated : c)) ?? prev)
  }

  async function handleApprove(id: string) {
    setBusyId(id)
    setError(null)
    try {
      updateChange(await applyVaultChange(id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusyId(null)
    }
  }

  async function handleReject(id: string) {
    setBusyId(id)
    setError(null)
    try {
      updateChange(await rejectVaultChange(id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="vault-ui">
      <h2>Vault Changes</h2>
      <button type="button" className="secondary" onClick={handleScan} disabled={scanning}>
        {scanning ? 'Scanning…' : 'Rescan vault'}
      </button>
      {scanSummary && <p className="subtitle">{scanSummary}</p>}
      {error && <div className="message error">{error}</div>}

      {!error && !changes && <p>Loading…</p>}

      {changes && changes.length === 0 && (
        <p className="subtitle">No pending changes.</p>
      )}

      {changes && changes.length > 0 && (
        <div className="change-list">
          {changes.map((change) => (
            <ChangeRow
              key={change.id}
              change={change}
              expanded={expandedId === change.id}
              busy={busyId === change.id}
              onToggle={() => setExpandedId((cur) => (cur === change.id ? null : change.id))}
              onApprove={() => handleApprove(change.id)}
              onReject={() => handleReject(change.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ChangeRow({
  change,
  expanded,
  busy,
  onToggle,
  onApprove,
  onReject,
}: {
  change: ChangeProposal
  expanded: boolean
  busy: boolean
  onToggle: () => void
  onApprove: () => void
  onReject: () => void
}) {
  const before = change.operation === 'create_file' ? '(new file)' : '(current content not available via this API)'

  return (
    <div className="change-row">
      <button type="button" className="change-header" onClick={onToggle}>
        <span className="change-path">{change.path}</span>
        <span className="operation-tag">{change.operation.replace(/_/g, ' ')}</span>
        <span className={`status-tag status-${change.status}`}>{change.status}</span>
      </button>
      {expanded && (
        <div className="change-details">
          {change.section && <p className="section-label">Section: {change.section}</p>}
          <div className="diff-columns">
            <div className="diff-column">
              <h4>Before</h4>
              <pre>{before}</pre>
            </div>
            <div className="diff-column">
              <h4>After</h4>
              <pre>{change.content}</pre>
            </div>
          </div>
          {change.error && <div className="message error">{change.error}</div>}
          {change.status === 'pending' && (
            <div className="change-actions">
              <button type="button" onClick={onApprove} disabled={busy}>
                {busy ? 'Working…' : 'Approve'}
              </button>
              <button type="button" className="secondary" onClick={onReject} disabled={busy}>
                Reject
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
