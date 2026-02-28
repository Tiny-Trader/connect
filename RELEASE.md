# Release Policy

This project follows Semantic Versioning (`MAJOR.MINOR.PATCH`) and releases from `main`.

## Versioning Rules

- `MAJOR`: breaking API or behavior changes.
- `MINOR`: backward-compatible features.
- `PATCH`: backward-compatible bug fixes, docs-only release fixes, and packaging corrections.

Examples:

- `0.1.0` -> `0.2.0`: add new non-breaking client methods.
- `0.2.3` -> `0.2.4`: fix parser bug without API change.
- `0.9.0` -> `1.0.0`: first stable release or intentional breaking contract updates.

## Release Source of Truth

1. Update `pyproject.toml` version.
2. Add a matching `CHANGELOG.md` entry under `## [X.Y.Z] - YYYY-MM-DD`.
3. Merge to `main`.
4. Create and push annotated tag `vX.Y.Z`.

Only tags in `v*.*.*` format trigger release publishing.

## Changelog Rules

- Every user-visible change must be documented.
- Group notes under:
  - `Added`
  - `Changed`
  - `Fixed`
  - `Security`
- Keep `Unreleased` section at top.

## Tag and Publish Pipeline

On tag push (`vX.Y.Z`), CI must pass:

1. tag/version match check (`vX.Y.Z` == `pyproject.toml` version),
2. changelog entry exists for `X.Y.Z`,
3. lint + typecheck + unit/integration tests,
4. package build.

Then pipeline publishes distributions and creates a GitHub Release.

## Hotfix Releases

1. Branch from `main` (`hotfix/<topic>`).
2. Apply minimal fix.
3. Bump `PATCH` version and update changelog.
4. Merge to `main` and tag `vX.Y.Z`.
5. Back-merge to `dev` when `dev` flow is active again.
