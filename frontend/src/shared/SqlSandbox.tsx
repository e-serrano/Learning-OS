import { type FormEvent, useState } from 'react'
import { ApiError, type SqlSandboxResult, runSql } from '../api/sandbox'
import './sql-sandbox.css'

/** "Try it" SQL console (docs/TASKS.md T137, user request via
 * AskUserQuestion, 2026-09-24): runs the user's own SQL against a
 * throwaway in-memory database for their own feedback before
 * answering -- purely informational, never fed into evaluation
 * (mastery/scoring stays AI-evaluation-derived, docs/AGENTS.md #9). */
export function SqlSandbox() {
  const [open, setOpen] = useState(false)
  const [sql, setSql] = useState('')
  const [result, setResult] = useState<SqlSandboxResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRun(event: FormEvent) {
    event.preventDefault()
    if (sql.trim().length === 0) return
    setBusy(true)
    setError(null)
    try {
      setResult(await runSql(sql))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the backend')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="sql-sandbox">
      <button type="button" className="secondary" onClick={() => setOpen((v) => !v)}>
        {open ? 'Hide SQL sandbox' : 'Try it: run SQL'}
      </button>
      {open && (
        <div className="sql-sandbox-panel">
          <form onSubmit={handleRun}>
            <label htmlFor="sandbox-sql">SQL</label>
            <textarea
              id="sandbox-sql"
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              rows={4}
              placeholder="CREATE TABLE t (id INTEGER); INSERT INTO t VALUES (1); SELECT * FROM t;"
            />
            <button type="submit" disabled={busy || sql.trim().length === 0}>
              {busy ? 'Running…' : 'Run'}
            </button>
          </form>
          {error && <div className="message error">{error}</div>}
          {result && <SqlSandboxOutput result={result} />}
        </div>
      )}
    </div>
  )
}

function SqlSandboxOutput({ result }: { result: SqlSandboxResult }) {
  if (result.error) {
    return <div className="message error">{result.error}</div>
  }
  if (result.columns.length === 0) {
    return <p className="sql-sandbox-hint">Ran with no result set.</p>
  }
  return (
    <>
      <table className="sql-sandbox-table">
        <thead>
          <tr>
            {result.columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell === null ? 'NULL' : String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {result.truncated && (
        <p className="sql-sandbox-hint">Showing first {result.row_count} rows.</p>
      )}
    </>
  )
}
