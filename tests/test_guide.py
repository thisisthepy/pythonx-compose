"""The guide checker (`.github/scripts/check_guide.py`) is part of the suite: it parses every page
under `docs/guide/`, resolves local links, and checks that English and Korean strings pair up."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / ".github" / "scripts" / "check_guide.py"


class TestGuide(unittest.TestCase):
    def test_guide_checker_reports_no_findings(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CHECKER)], cwd=REPO, capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("0 findings", result.stdout)


if __name__ == "__main__":
    unittest.main()
