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

```text
main ← pull request ← feature/<task-id>-<short-name>
```

CI must be green before merging to `main`.

## Quality gates

Backend:

```bash
uv run pytest
uv run ruff check .
uv run mypy backend/app
```

Frontend:

```bash
npm test
npm run build
```

Do not commit or push code that fails these checks, contains secrets, or breaks existing functionality.
