# Release and Versioning Strategy

This document defines the branch flow, version bump automation, and publishing model for `tt-connect`.

## Goals

- Releases are explicit, intentional actions — not side effects of merging.
- `main` is the only long-lived branch and the source for production publishing.
- Release mechanics are reproducible, observable, and low-risk.

## Branch Model

- `feat/*`, `fix/*`, `chore/*` -> PR into `main`
- `main` -> stable, always-releasable trunk

## Versioning Standard

Use Semantic Versioning (`MAJOR.MINOR.PATCH`):

- `MAJOR`: breaking API changes
- `MINOR`: backward-compatible features
- `PATCH`: backward-compatible bug fixes

## Changelog Convention

All PRs with user-visible changes must add entries under `## [Unreleased]` in `CHANGELOG.md`.
The release workflow stamps the heading with the version number and date at release time.

## Release Workflow

Releases are triggered manually via GitHub Actions:

```bash
gh workflow run release.yml -f bump=patch   # or minor, major
```

The `release.yml` workflow:

1. Bumps the version in `pyproject.toml`.
2. Inserts `## [X.Y.Z] - YYYY-MM-DD` immediately below `## [Unreleased]` in `CHANGELOG.md`.
3. Commits `chore(release): vX.Y.Z` and creates tag `vX.Y.Z`.
4. Pushes commit + tag atomically to `main`.

The tag push automatically triggers `publish-main.yml`.

## Publishing Policy

- Production publish only from `main`.
- Publishing is triggered by Git tag on `main`: `vX.Y.Z`.
- Workflow validates:
  - tag version equals `pyproject.toml` version
  - tag commit is on `main`
  - quality gates pass (`make ci`)
  - package build passes (`poetry build`)
- On success:
  - publish wheel + sdist to PyPI
  - create GitHub Release notes from GitHub metadata and attach built artifacts

## Security and Credentials

Use PyPI Trusted Publisher (OIDC) for GitHub Actions.

- Avoid long-lived PyPI tokens in repository secrets.
- Restrict release workflow permissions to minimum required scope.
- `RELEASE_BYPASS_TOKEN` (fine-grained PAT, `contents:write`) must be stored as a
  secret on the protected `release` environment (restricted to `main` with
  required reviewers). The release workflow uses it to push the version bump
  commit and tag past branch protection.

## Required CI Workflows

1. `connect-ci.yml`
   - lint, typecheck, tests, coverage, package build, docs build
   - runs on all PRs to `main` and pushes to `main`
2. `changelog-check.yml`
   - ensures `CHANGELOG.md` is updated for code-impacting PRs
3. `release.yml`
   - manual workflow dispatch to bump version, tag, and push
4. `publish-main.yml`
   - runs on `push` tag `v*.*.*` only
   - verifies branch/tag/version alignment
   - publishes to PyPI and creates release
   - pins third-party GitHub Actions to immutable commit SHAs

## Branch Protection Rules

### `main`

- Require pull request
- Require status checks
- Require branch up to date
- Block direct pushes (bypass for release workflow via PAT)

### Tags (`v*`)

- Block deletion
- Block non-fast-forward updates

## Local Developer Expectations

- Use pre-commit hooks for fast feedback (`ruff`, `mypy`).
- CI is the source of truth for release gate conditions.
- Do not manually edit version during feature PRs.

## Failure Handling

- If release workflow fails, fix root cause and re-run the workflow.
- If publish job fails on tag, fix root cause first. Prefer rerun on same tag; if the fix
  is a workflow change on `main`, retarget the tag once to the fixed commit and republish.
- If broken package is published, release next patch (`X.Y.(Z+1)`) with remediation notes.
