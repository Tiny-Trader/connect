# Contributing to tt-connect

## Branch Strategy (Current)

Until `main` is fully stabilized, we use a `main`-first flow.

Use these branch names:

- `main`: source of truth.
- `feat/<topic>`: feature work from `main`.
- `fix/<topic>`: bug fixes from `main`.
- `hotfix/<topic>`: urgent production fixes from `main`.

## Merge Flow

1. Branch from `main`.
2. Open PR into `main`.
3. Merge only after CI passes and review is complete.
4. Use release tags (`vX.Y.Z`) from `main` per `RELEASE.md`.

## PR Rules

Every PR should include:

1. Problem and change summary.
2. Test evidence (commands run, output summary).
3. Any risk/rollback notes.
4. `CHANGELOG.md` update for user-visible changes to code, behavior, or APIs.

## CI Policy

- PRs to `main` must pass:
  - lint (`ruff`)
  - type check (`mypy`)
  - tests (`pytest` unit + integration)
  - coverage gate (`>=64%` for `tt_connect`, raise as coverage improves)
  - package build (`poetry build`)
  - changelog gate for code-impacting changes
- Live tests under `tests/live/` are manual and not part of required CI.

## Local Developer Commands

Use `make` targets from `connect/`:

- `make lint`
- `make typecheck`
- `make test`
- `make test-fast`
- `make coverage`
- `make precommit-install`
- `make precommit-run`

## Branch Protection Settings (GitHub)

Apply these rules to `main`:

1. Require pull request before merging.
2. Require at least 1 approval.
3. Require status checks to pass.
4. Require branches to be up to date before merge.
5. Disable force pushes and branch deletion.
