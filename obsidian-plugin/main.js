// Learning OS: Pending Changes -- Obsidian plugin (docs/TASKS.md T136).
//
// Hardcodes the backend's documented default dev port (DEVELOPMENT.md:
// `uv run uvicorn app.main:app --reload`, no --port flag = 8000). A
// settings tab for a configurable base URL is a natural follow-up, out
// of scope for this MVP (same simplification T135's extension made).
//
// Uses Obsidian's `requestUrl` instead of plain `fetch` -- Obsidian's
// own docs recommend it specifically because it bypasses the renderer's
// CORS enforcement, the same reason T135's browser extension routes
// every request through its background service worker rather than a
// content script. No plain `fetch()` calls from this plugin.
//
// Hand-written plain JS, no bundler/TypeScript build step -- Obsidian
// loads `main.js` directly via CommonJS `require`, and a single-file
// plugin this small doesn't need one, matching T135's "no new build
// tooling" choice for the browser extension.
const { Plugin, ItemView, Notice, requestUrl } = require('obsidian')

const VIEW_TYPE = 'learning-os-pending-changes'
const API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
const PREVIEW_LENGTH = 200
const ACTION_PAST_TENSE = { apply: 'applied', reject: 'rejected' }

class PendingChangesView extends ItemView {
  getViewType() {
    return VIEW_TYPE
  }

  getDisplayText() {
    return 'Learning OS: Pending changes'
  }

  getIcon() {
    return 'git-pull-request'
  }

  async onOpen() {
    await this.refresh()
  }

  async refresh() {
    const container = this.containerEl.children[1]
    container.empty()

    const header = container.createDiv({ cls: 'learning-os-header' })
    header.createEl('h4', { text: 'Pending vault changes' })
    const refreshBtn = header.createEl('button', { text: 'Refresh' })
    refreshBtn.addEventListener('click', () => this.refresh())

    let changes
    try {
      const response = await requestUrl({ url: `${API_BASE_URL}/vault/changes`, method: 'GET' })
      changes = response.json.changes
    } catch (err) {
      container.createEl('p', {
        text: `Could not reach Learning OS: ${err.message || err}`,
        cls: 'learning-os-error',
      })
      return
    }

    if (changes.length === 0) {
      container.createEl('p', { text: 'No pending changes.', cls: 'learning-os-empty' })
      return
    }

    for (const change of changes) {
      const item = container.createDiv({ cls: 'learning-os-change' })
      item.createEl('div', { text: change.path, cls: 'learning-os-change-path' })
      item.createEl('div', { text: change.operation, cls: 'learning-os-change-op' })
      const preview =
        change.content.length > PREVIEW_LENGTH
          ? `${change.content.slice(0, PREVIEW_LENGTH)}…`
          : change.content
      item.createEl('pre', { text: preview, cls: 'learning-os-change-preview' })

      const actions = item.createDiv({ cls: 'learning-os-change-actions' })
      const applyBtn = actions.createEl('button', { text: 'Apply', cls: 'mod-cta' })
      applyBtn.addEventListener('click', () => this.act(change.id, 'apply'))
      const rejectBtn = actions.createEl('button', { text: 'Reject' })
      rejectBtn.addEventListener('click', () => this.act(change.id, 'reject'))
    }
  }

  async act(changeId, action) {
    try {
      await requestUrl({
        url: `${API_BASE_URL}/vault/changes/${changeId}/${action}`,
        method: 'POST',
      })
      new Notice(`Change ${ACTION_PAST_TENSE[action]}`)
    } catch (err) {
      new Notice(`Could not ${action} change: ${err.message || err}`)
    }
    await this.refresh()
  }
}

module.exports = class LearningOSPlugin extends Plugin {
  async onload() {
    this.registerView(VIEW_TYPE, (leaf) => new PendingChangesView(leaf))

    this.addRibbonIcon('git-pull-request', 'Learning OS: Pending changes', () => {
      this.activateView()
    })

    this.addCommand({
      id: 'learning-os-open-pending-changes',
      name: 'Open pending changes',
      callback: () => this.activateView(),
    })
  }

  onunload() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE)
  }

  async activateView() {
    const { workspace } = this.app
    let leaf = workspace.getLeavesOfType(VIEW_TYPE)[0]
    if (!leaf) {
      leaf = workspace.getRightLeaf(false)
      await leaf.setViewState({ type: VIEW_TYPE, active: true })
    }
    workspace.revealLeaf(leaf)
  }
}
