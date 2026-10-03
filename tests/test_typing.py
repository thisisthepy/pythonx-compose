"""A type checker reads the committed stubs the way the interpreter resolves names.

Each case is a small program type-checked by mypy against this checkout's `pythonx.compose` stubs
(`MYPYPATH` is the repository root). Correct code must pass; a misspelled keyword or function must
fail, naming what is wrong, because a stub that accepts everything proves nothing.

Needs `mypy` importable in the running interpreter; without it the tests skip, and a skip is not a
pass.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRATCH = REPO / ".tmp"


def _mypy(program: str) -> tuple[int, str]:
    """mypy's exit code and output for one program, with this checkout's stubs on the path."""
    SCRATCH.mkdir(exist_ok=True)
    SCRATCH.mkdir(exist_ok=True)  # git-ignored, so absent on a fresh checkout such as CI's
    with tempfile.TemporaryDirectory(dir=SCRATCH) as scratch:
        source = Path(scratch) / "program.py"
        source.write_text(textwrap.dedent(program), encoding="utf-8")
        env = {**os.environ, "MYPYPATH": str(REPO)}
        done = subprocess.run(
            [sys.executable, "-m", "mypy", "--no-error-summary", "--show-error-codes",
             "--cache-dir", str(Path(scratch) / "cache"), "--python-version", "3.11", str(source)],
            cwd=REPO, env=env, capture_output=True, text=True,
        )
        return done.returncode, done.stdout + done.stderr


class TheStubsTypeCheck(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("mypy") is None:
            raise unittest.SkipTest("mypy is not installed; the stubs cannot be type-checked here")

    def assertPasses(self, program: str) -> None:
        code, output = _mypy(program)
        self.assertEqual(0, code, output)
        self.assertEqual("", output.strip())

    def assertFails(self, program: str, *expected: str) -> None:
        code, output = _mypy(program)
        self.assertEqual(1, code, output)
        for fragment in expected:
            self.assertIn(fragment, output)

    def test_the_notebook_imports_and_a_modifier_chain_pass(self):
        self.assertPasses("""
            from pythonx.compose.layout import Column, Arrangement
            from pythonx.compose.ui import Modifier, Alignment
            from pythonx.compose.material3 import Text, Column as M3Column, Row, Spacer
            from pythonx.compose.runtime import Composable

            def chain(m: Modifier) -> Modifier:
                return m.padding(16).fill_max_width()

            @Composable
            def Screen() -> None:
                Column(
                    vertical_arrangement=Arrangement.SpaceBetween,
                    horizontal_alignment=Alignment.CenterHorizontally,
                    content=lambda scope: Text("hi", font_size=20),
                )
                M3Column(content=lambda scope: None)
        """)

    def test_every_committed_stub_type_checks(self):
        """mypy reports errors inside a stub it reads from the search path, so this checks them all."""
        import tomllib

        with (REPO / "pythonx" / "compose" / "pythonx-map.toml").open("rb") as handle:
            modules = sorted(tomllib.load(handle)["modules"])
        self.assertPasses("".join(f"import {module}\n" for module in modules))

    def test_a_methods_keywords_are_snake_case_in_the_stubs(self):
        """SPEC S4.1: the stubs are Pythonic-only; the runtime also accepts Kotlin's spelling."""
        self.assertPasses("""
            from pythonx.compose.ui import Modifier

            Modifier.padding(padding_values=None)
        """)
        self.assertFails("""
            from pythonx.compose.ui import Modifier

            Modifier.padding(paddingValues=None)
        """, '"paddingValues"', 'did you mean "padding_values"')

    def test_a_modifier_chain_on_the_class_passes(self):
        self.assertPasses("""
            from pythonx.compose.ui import Modifier

            m: Modifier = Modifier.padding(16).fill_max_width()
        """)

    def test_a_misspelled_keyword_fails(self):
        self.assertFails("""
            from pythonx.compose.material3 import Text

            Text("hi", fontSize=20)
        """, '"fontSize"', 'did you mean "font_size"')

    def test_a_misspelled_function_fails(self):
        self.assertFails("""
            from pythonx.compose.ui import Modifier

            Modifier.padding(16).fillMaxWidth()
        """, '"fillMaxWidth"', "[attr-defined]")

    def test_a_grouped_constant_type_checks(self):
        """SPEC S7.1: `Alignment.Horizontal.End` beside `Alignment.End`; `Top` is no `Horizontal`."""
        self.assertPasses("""
            from pythonx.compose.ui import Alignment
            from pythonx.compose.layout import Arrangement

            a = Alignment.Horizontal.End
            b = Alignment.End
            c = Arrangement.HorizontalOrVertical.SpaceBetween
        """)
        self.assertFails("""
            from pythonx.compose.ui import Alignment

            Alignment.Horizontal.Top
        """, '"Top"', "[attr-defined]")

    def test_an_object_function_and_nested_types_type_check(self):
        """SPEC S7.1: `Arrangement.spaced_by` is a static method; a nested type is the group too."""
        self.assertPasses("""
            from pythonx.compose.layout import Arrangement, Column
            from pythonx.compose.ui import Alignment

            a = Arrangement.spaced_by(8)
            Column(vertical_arrangement=a, horizontal_alignment=Alignment.Horizontal.End, content=lambda scope: None)
            Column(horizontal_alignment=Alignment.CenterHorizontally, content=lambda scope: None)
        """)
        self.assertFails("""
            from pythonx.compose.layout import Arrangement

            Arrangement.spacedBy(8)
        """, '"spacedBy"', "[attr-defined]")
        self.assertFails("""
            from pythonx.compose.layout import Column
            from pythonx.compose.ui import Alignment

            Column(horizontal_alignment=Alignment.Vertical.Top, content=lambda scope: None)
        """, "[arg-type]")

    def test_a_property_and_its_setter_type_check(self):
        self.assertPasses("""
            from pythonx.compose.ui import ImageComposeScene

            def flip(scene: ImageComposeScene) -> None:
                scene.layout_direction = scene.layout_direction
        """)

    def test_a_kotlin_spelled_module_function_fails(self):
        self.assertFails("""
            from pythonx.compose.layout import fillMaxWidth
        """, "fillMaxWidth", "[attr-defined]")


if __name__ == "__main__":
    unittest.main()
