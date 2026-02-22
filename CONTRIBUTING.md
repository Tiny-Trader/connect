# Contributing to tt-connect

## Branch Strategy (Short GitFlow)

Use these branch names:

- `main`: production-grade code only.
- `dev`: integration branch for upcoming release.
- `feat/<topic>`: new features from `dev`.
- `fix/<topic>`: non-urgent fixes from `dev`.
- `rel/<version>`: release hardening from `dev` (example: `rel/0.3.0`).
- `hotfix/<topic>`: urgent fixes from `main`.

## Merge Flow

1. Branch from `dev` for regular work (`feat/*`, `fix/*`).
2. Open PR into `dev` and merge only after CI passes.
3. Cut `rel/*` from `dev` when stabilizing a release.
4. Merge `rel/*` into `main`, tag release, then merge back into `dev`.
5. For incidents, branch `hotfix/*` from `main`, then merge to both `main` and `dev`.

## PR Rules

Every PR should include:

1. Problem and change summary.
2. Test evidence (commands run, output summary).
3. Any risk/rollback notes.

## CI Policy

- PRs to `dev` and `main` must pass:
  - lint (`ruff`)
  - type check (`mypy`)
  - tests (`pytest` unit + integration)
  - coverage gate (`>=85%` for `tt_connect`)
  - package build (`poetry build`)
- Live tests under `tests/live/` are manual and not part of required CI.

## Local Developer Commands

These shortcuts are defined in `pyproject.toml`:

- `poetry run tt-lint`
- `poetry run tt-typecheck`
- `poetry run tt-test`
- `poetry run tt-test-fast`
- `poetry run tt-coverage`
- `poetry run tt-precommit-install`
- `poetry run tt-precommit-run`

## Branch Protection Settings (GitHub)

Apply these rules to `main` and `dev`:

1. Require pull request before merging.
2. Require at least 1 approval.
3. Require status checks to pass.
4. Require branches to be up to date before merge.
5. Disable force pushes and branch deletion.
