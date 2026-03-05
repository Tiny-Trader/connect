## Release PR: `dev` -> `main`

Use this template only for release merges from `dev` into `main`.

## Release Summary

- Target version in `pyproject.toml`:
- Linked changelog entry:
- Included PR range / notable changes:

## Version + Tag Plan

- [ ] Version is already bumped on `dev` (do **not** bump again in this PR)
- [ ] `CHANGELOG.md` has the correct release entry
- [ ] Post-merge tag to create on `main`: `vX.Y.Z` (must match `pyproject.toml`)

## Release Validation

Paste commands and short outputs:

```bash
make lint
make typecheck
make test-fast
make coverage
make docs-build
```

## Publish Checklist

- [ ] I verified release workflow preconditions in `.github/workflows/publish-main.yml`
- [ ] I will create/push the tag **after** merge to `main`
- [ ] I confirmed tag format: `v<pyproject version>`

## Risk and Rollback

- Main release risks:
- Rollback plan (tag/release/package):

## Notes

- Semver labels are required for PRs into `dev`, not for this `dev -> main` release PR.
