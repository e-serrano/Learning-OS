# Contributing

## Branches

```text
main                        stable, protected
feature/<task-id>-<name>    new functionality (e.g. feature/T020-vault-onboarding)
fix/<task-id>-<name>        bug fixes
chore/<task-id>-<name>      internal/maintenance work
```

`develop` is not used in this repository.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>
```

Allowed types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `ci`, `perf`.

Reference the task ID when it adds clarity, e.g. `feat(onboarding): add vault configuration [T020]`.

## Workflow

`main` requires its 3 CI checks (`backend`, `frontend`, `e2e`) to pass and
blocks force-push/deletion, but does not require a pull request — this
project has one active maintainer plus an AI coding agent, both pushing
directly to `main` after running the quality gates below locally. Use a
`feature/<task-id>-<short-name>` branch and a pull request when you want
review before merging, e.g. an external contribution:

```text
main ← pull request ← feature/<task-id>-<short-name>
```

Either way, CI must be green before/at merge to `main`.

## Quality gates

Backend (from `backend/`):

```bash
uv run ruff format
uv run ruff check --fix .
uv run pytest -q
uv run mypy app
```

Frontend (from `frontend/`):

```bash
npm test
npm run build
npm run lint
```

Do not commit or push code that fails these checks, contains secrets, or breaks existing functionality.
