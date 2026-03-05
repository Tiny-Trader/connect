## Summary

> For `dev -> main` release PRs, use `.github/PULL_REQUEST_TEMPLATE/release-dev-to-main.md`.

- What problem does this PR solve?
- What changed?

## Semver Label (Required)

Select exactly one label on this PR:

- `semver:major` for breaking changes
- `semver:minor` for backward-compatible features
- `semver:patch` for backward-compatible fixes

> PRs to `dev` are expected to carry exactly one semver label.

## Release Impact

- User-visible behavior changes:
- API/signature changes:
- Migration notes (if any):

## Test Evidence

Paste commands and short outputs:

```bash
make lint
make typecheck
make test-fast
make coverage
```

## Risk and Rollback

- Main risks:
- How to rollback safely:

## Checklist

- [ ] I added exactly one semver label (`semver:major|minor|patch`)
- [ ] I ran local quality gates and included evidence
- [ ] I updated docs when behavior/API changed
- [ ] I considered changelog/release impact
- [ ] I read [`docs/RELEASE_VERSIONING.md`](./docs/RELEASE_VERSIONING.md)
