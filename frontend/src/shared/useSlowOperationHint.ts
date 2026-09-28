import { useEffect, useState } from 'react'

/** True once `active` has stayed true for longer than `afterMs` (docs/TASKS.md
 * T151, dogfood ISSUE-005): an AI-backed action can legitimately take up to
 * ~2 minutes -- RetryingProvider tries the primary model (up to a 60s
 * timeout), then falls back to a second one (another up to 60s) -- with
 * nothing distinguishing that from a hang in the UI. This lets a caller show
 * a "this can take a while" hint instead of leaving a bare spinner/disabled
 * button that looks broken. */
export function useSlowOperationHint(active: boolean, afterMs = 8000): boolean {
  const [showHint, setShowHint] = useState(false)

  useEffect(() => {
    if (!active) {
      setShowHint(false)
      return
    }
    const timer = setTimeout(() => setShowHint(true), afterMs)
    return () => clearTimeout(timer)
  }, [active, afterMs])

  return showHint
}
