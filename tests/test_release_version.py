"""The release gate (`.github/scripts/check_release_version.py`): a tag publishes only when it is
`v` + the version in `pyproject.toml`. Run both ways -- a match passes, anything else fails."""

from __future__ import annotations

import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_release_version.py"
VERSION = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def _run(tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), tag], cwd=REPO, capture_output=True, text=True)


class TestReleaseVersion(unittest.TestCase):
    def test_matching_tag_passes(self) -> None:
        result = _run(f"v{VERSION}")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_ref_form_of_the_tag_passes(self) -> None:
        self.assertEqual(0, _run(f"refs/tags/v{VERSION}").returncode)

    def test_mismatched_tag_fails_and_names_both(self) -> None:
        result = _run("v9.9.9")
        self.assertEqual(1, result.returncode)
        self.assertIn("v9.9.9", result.stderr)
        self.assertIn(f"v{VERSION}", result.stderr)

    def test_tag_without_the_v_prefix_fails(self) -> None:
        self.assertEqual(1, _run(VERSION).returncode)

    def test_a_prefix_of_the_version_fails(self) -> None:
        self.assertEqual(1, _run(f"v{VERSION}.post1").returncode)

    def test_no_argument_fails(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
