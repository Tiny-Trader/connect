# Contributing to tt-connect

## Branch Strategy (Current)

We use a `dev`-first integration flow, then promote stable changes to `main`.

Use these branch names:

- `dev`: integration branch for ongoing work.
- `main`: stable release branch.
- `feat/<topic>`: feature work from `dev`.
- `fix/<topic>`: bug fixes from `dev`.
- `hotfix/<topic>`: urgent production fixes from `main` (can be cherry-picked back to `dev`).

## Merge Flow

1. Branch from `dev` for regular changes (`hotfix/*` may branch from `main` when urgent).
2. Open PR into `dev` for regular changes.
3. Merge only after CI passes and review is complete.
4. Promote `dev` to `main` when ready for release.
5. Use release tags (`vX.Y.Z`) from `main` per release policy.

## PR Rules

Every PR should include:

1. Problem and change summary.
2. Test evidence (commands run, output summary).
3. Any risk/rollback notes.
4. `CHANGELOG.md` update for user-visible changes to code, behavior, or APIs.
5. Exactly one semver label (`semver:major`, `semver:minor`, or `semver:patch`) for PRs targeting `dev`.

## CI Policy

- PRs to `dev` and `main` must pass:
  - lint (`ruff`)
  - type check (`mypy`)
  - tests (`pytest` unit + integration)
  - coverage gate (`>=64%` for `tt_connect`, raise as coverage improves)
  - package build (`poetry build`)
  - changelog gate for code-impacting changes
- PRs to `dev` must also pass semver label gate (`semver:major|minor|patch`).
- Live tests under `tests/live/` are manual and not part of required CI.
- Release and versioning automation policy is documented in [`docs/RELEASE_VERSIONING.md`](./docs/RELEASE_VERSIONING.md).

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

Branch governance is managed through GitHub rulesets for both `dev` and `main`.

1. Require pull request before merging.
2. Require status checks to pass.
3. Require branches to be up to date before merge.
4. Block direct pushes to protected branches.
5. For `dev`, enforce exactly one semver label via required check.
