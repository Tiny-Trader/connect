#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <tag>" >&2
  exit 2
fi

tag="$1"
if [[ ! "$tag" =~ ^v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  echo "invalid tag format: '$tag' (expected vX.Y.Z)" >&2
  exit 1
fi

tag_version="${BASH_REMATCH[1]}"
project_version="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -n 1)"

if [[ -z "$project_version" ]]; then
  echo "could not parse version from pyproject.toml" >&2
  exit 1
fi

if [[ "$tag_version" != "$project_version" ]]; then
  echo "tag/version mismatch: tag=$tag_version pyproject=$project_version" >&2
  exit 1
fi

echo "release version check passed: $tag"
