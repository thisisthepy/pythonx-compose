#!/usr/bin/env python3
"""Fail unless a release tag is `v` + the version in `pyproject.toml`.

    python3 .github/scripts/check_release_version.py "$GITHUB_REF_NAME"   # exit 0 = match, 1 = not

`publish-pypi.yml` runs this before building, so a tag cannot publish a version it does not name.
A full ref (`refs/tags/v0.1.0a1`) is accepted too. Standard library only.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_release_version.py <tag>", file=sys.stderr)
        return 2
    tag = argv[1].removeprefix("refs/tags/")
    with open(REPO / "pyproject.toml", "rb") as f:
        version = tomllib.load(f)["project"]["version"]
    expected = f"v{version}"
    if tag != expected:
        print(f"error: tag {tag!r} does not match pyproject.toml, which expects {expected!r}.\n"
              f"Fix the version in pyproject.toml or tag the right commit.", file=sys.stderr)
        return 1
    print(f"ok: tag {tag} matches pyproject.toml version {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
