"""Optional, opt-in git auto-commit for vault writes (docs/TASKS.md
T138, docs/AGENTS.md #22: "If Git is present ... Automatic commits are
opt-in").

Only ever commits the single file `ApplyChangeService` just wrote --
never `git add -A`/`git commit -a` -- so an unrelated dirty change
elsewhere in the vault's working tree is never swept into our commit
(docs/AGENTS.md #22: "never overwrite unrelated dirty changes"). Never
resets, never force-pushes, never deletes anything, and never pushes to
any remote -- this is local commit history only, the same
loopback/local-first scope as the rest of the app (docs/AGENTS.md #19,
#25). Best-effort: a git failure (not a repo, git not installed,
nothing changed to commit) never blocks or fails the vault write that
triggered it -- same defensive-optional-collaborator shape as
`MasteryCurationTriggerService` (docs/TASKS.md T139).
"""

import subprocess

from app.obsidian.vault_resolver import VaultResolver

GIT_TIMEOUT_SECONDS = 5.0


class VaultGitService:
    def __init__(self, vault: VaultResolver) -> None:
        self._vault = vault

    def is_git_repo(self) -> bool:
        result = self._run("rev-parse", "--is-inside-work-tree")
        return result is not None and result.returncode == 0 and result.stdout.strip() == "true"

    def commit_file(self, relative_path: str, message: str) -> bool:
        """Stages and commits exactly this one file. Returns whether a
        commit was actually made -- False (never an exception) for "not
        a git repo", "git not installed/not on PATH", or "nothing
        changed" (the file's content already matches HEAD, so there is
        nothing staged for `commit` to record)."""
        if not self.is_git_repo():
            return False
        target = self._vault.resolve(relative_path)
        added = self._run("add", "--", str(target))
        if added is None or added.returncode != 0:
            return False
        committed = self._run("commit", "-m", message, "--", str(target))
        return committed is not None and committed.returncode == 0

    def _run(self, *args: str) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                ["git", "-C", str(self._vault.root), *args],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
