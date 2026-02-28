# Release and Versioning Strategy

This document defines the branch flow, version bump automation, and publishing model for `tt-connect`.

## Goals

- Every merge to `dev` triggers deterministic version bump automation.
- `main` is the only source for production package publishing.
- Release mechanics are reproducible, observable, and low-risk.

## Branch Model

- `feat/*`, `fix/*`, `hotfix/*`, `chore/*` -> PR into `dev`
- `dev` -> integration branch with automated versioning
- `main` -> stable release branch, publish source of truth

## Versioning Standard

Use Semantic Versioning (`MAJOR.MINOR.PATCH`):

- `MAJOR`: breaking API changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible bug fixes

## Bump Trigger on `dev`

On merge to `dev`, CI determines bump level from PR label:

- `semver:major`
- `semver:minor`
- `semver:patch`

Rules:

1. Exactly one semver label is required.
2. If label is missing or multiple labels are present, the merge gate fails.
3. The bump workflow updates:
   - `pyproject.toml` version
   - `CHANGELOG.md`
4. Bot commits the bump back to `dev`:
   - `chore(release): bump version to X.Y.Z`

## Publishing Policy

- Production publish only from `main`.
- Publishing is triggered by Git tag on `main`: `vX.Y.Z`.
- Workflow validates:
  - tag version equals `pyproject.toml` version
  - full CI checks passed
  - package build passes (`poetry build`)
- On success:
  - publish wheel + sdist to PyPI
  - create GitHub Release notes with changelog slice

Optional:

- Publish prereleases from `dev` to TestPyPI using `X.Y.Z.devN`.

## Security and Credentials

Use PyPI Trusted Publisher (OIDC) for GitHub Actions.

- Avoid long-lived PyPI tokens in repository secrets.
- Restrict release workflow permissions to minimum required scope.
- If `dev` is PR-locked by rulesets, store a fine-grained PAT (contents:write)
  as `RELEASE_BYPASS_TOKEN` for version-bump automation.

## Required CI Workflows

1. `connect-ci.yml`
   - lint, typecheck, tests, coverage, package build
   - includes `require_single_semver_label` check for PRs targeting `dev`
2. `version-bump-dev.yml`
   - runs on merge to `dev`
   - validates semver label
   - bumps version + changelog and pushes bot commit
   - uses `RELEASE_BYPASS_TOKEN` when direct bot push is blocked by rulesets
3. `publish-main.yml`
   - runs on `push` tag `v*.*.*` only
   - verifies branch/tag/version alignment
   - publishes to PyPI and creates release
   - pins third-party GitHub Actions to immutable commit SHAs

## Branch Protection Rules

### `dev`

- Require pull request
- Require status checks
- Require branch up to date
- Require semver-label check
- Block direct pushes

### `main`

- Require pull request
- Require status checks
- Require branch up to date
- Restrict merge source to `dev` (via policy or CODEOWNERS + review gate)
- Block direct pushes

## Local Developer Expectations

- Use pre-commit hooks for fast feedback (`ruff`, `mypy`).
- CI is the source of truth for release gate conditions.
- Do not manually edit version during feature PRs.

## Failure Handling

- If version bump job fails on `dev`, block further promotion until fixed.
- If publish job fails on `main`, do not retag blindly. Fix and rerun workflow against same tag when possible.
- If broken package is published, release next patch (`X.Y.(Z+1)`) with remediation notes.
