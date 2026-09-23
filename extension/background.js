// Learning OS Web Clipper -- background service worker (docs/TASKS.md T135).
//
// Hardcodes the backend's documented default dev port (DEVELOPMENT.md:
// `uv run uvicorn app.main:app --reload`, no --port flag = 8000). A
// configurable base URL (options page) is a natural follow-up, out of
// scope for this MVP.
//
// Fetching from a MV3 background service worker with `host_permissions`
// covering the target origin is exempt from CORS -- unlike a content
// script or popup page, which run in the *visited page's* origin and
// would need the backend's CORS allowlist extended. Routing every
// request through this service worker means the backend's existing
// `allow_origins` (locked to the Vite dev origin, docs/API_SPEC.md #12)
// never needs to change for this extension to work.
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const MENU_ID = 'learning-os-clip-selection'
const BADGE_CLEAR_DELAY_MS = 4000

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: 'Save selection to Learning OS',
    contexts: ['selection'],
  })
})

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID || !info.selectionText) return
  saveClip(info.pageUrl ?? tab?.url ?? '', tab?.title ?? '', info.selectionText)
})

async function saveClip(url, title, selection) {
  try {
    const response = await fetch(`${API_BASE_URL}/vault/clip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, title, selection }),
    })

    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.error?.message ?? `Request failed (${response.status})`)
    }

    showBadge('OK', '#16a34a')
  } catch (err) {
    console.error('Learning OS clip failed:', err)
    showBadge('ERR', '#dc2626')
  }
}

function showBadge(text, color) {
  chrome.action.setBadgeText({ text })
  chrome.action.setBadgeBackgroundColor({ color })
  setTimeout(() => chrome.action.setBadgeText({ text: '' }), BADGE_CLEAR_DELAY_MS)
}
