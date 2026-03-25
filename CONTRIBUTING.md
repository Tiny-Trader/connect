# Contributing to tt-connect

## Branch Strategy

We use trunk-based development with a single `main` branch.

- `main`: stable, always-releasable branch.
- `feat/<topic>`: feature work branched from `main`.
- `fix/<topic>`: bug fixes branched from `main`.
- `chore/<topic>`: maintenance work branched from `main`.

## Merge Flow

1. Branch from `main`.
2. Open PR into `main`.
3. Merge only after CI passes and review is complete.
4. Releases are cut via `gh workflow run release.yml -f bump=patch|minor|major`.

## PR Rules

Every PR should include:

1. Problem and change summary.
2. Test evidence (commands run, output summary).
3. Any risk/rollback notes.
4. `CHANGELOG.md` update under `## [Unreleased]` for user-visible changes.

## CI Policy

- PRs to `main` must pass:
  - lint (`ruff`)
  - type check (`mypy`)
  - tests (`pytest` unit + integration)
  - coverage gate (`>=64%` for `tt_connect`, raise as coverage improves)
  - package build (`poetry build`)
  - changelog gate for code-impacting changes
- Live tests under `tests/live/` are manual and not part of required CI.
- Release and versioning policy is documented in [`docs/RELEASE_VERSIONING.md`](./docs/RELEASE_VERSIONING.md).

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

Branch governance is managed through a GitHub ruleset for `main`.

1. Require pull request before merging.
2. Require status checks to pass.
3. Require branches to be up to date before merge.
4. Block direct pushes to protected branches.
