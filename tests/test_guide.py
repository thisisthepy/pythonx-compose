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

    def test_getting_started_and_concepts_have_scroll_driven_live_previews(self) -> None:
        guide = REPO / "docs" / "guide"
        for page_name in ("getting-started.html", "concepts.html"):
            with self.subTest(page=page_name):
                text = (guide / page_name).read_text(encoding="utf-8")
                self.assertIn("live-layout", text)
                self.assertIn("live-stage", text)
                self.assertIn("data-live-step=", text)
                self.assertIn("data-live-scene=", text)
                self.assertIn("live-line is-changed", text)
        css = (guide / "assets" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".live-layout", css)
        self.assertIn("prefers-reduced-motion: reduce", css)
        js = (guide / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn("IntersectionObserver", js)
        self.assertIn("prefers-reduced-motion", js)

    def test_runtime_paths_guide_page_covers_all_three_paths(self) -> None:
        page = REPO / "docs" / "guide" / "guide-runtimes.html"
        self.assertTrue(page.is_file(), "docs/guide/guide-runtimes.html is missing")
        text = page.read_text(encoding="utf-8")
        for expected in (
            "ApplicationOutput.NativeImage",
            "-Dcompose.awt=false",
            "org.thisisthepy.kotlin.native.desktop",
            "macosArm64()",
            "linuxX64()",
            "uv add --prerelease allow pythonx-compose",
            "ppp core add",
            "tcl install pythonx-compose",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
