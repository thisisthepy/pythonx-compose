"""What the wheel actually carries -- built, opened and listed, not inferred from `package-data`.

AGENTS.md section 15: a pattern in `pyproject.toml` is not proof that a file ships. This builds the
wheel from a copy of the sources (so no `build/` or `*.egg-info` lands in the checkout) and reads its
file list.

Needs `setuptools` and `wheel` importable in the running interpreter; without them the test skips,
and a skip is not a pass.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRATCH = REPO / ".tmp"


def _build_wheel(out: Path) -> Path:
    source = out / "src"
    shutil.copytree(
        REPO, source,
        ignore=shutil.ignore_patterns(".git", ".tmp", ".worktrees", "build", "*.egg-info",
                                      "__pycache__", "UI.ipynb", "test", "docs", "tools"),
    )
    wheels = out / "wheels"
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(source), "--no-deps", "--no-build-isolation",
         "-q", "-w", str(wheels)],
        check=True, capture_output=True, text=True,
    )
    (wheel,) = wheels.glob("*.whl")
    return wheel


_SCENARIO = """
import sys
from pathlib import Path
sys.path.insert(0, {tests!r})
import adapter, fake_host
adapter._REPO = Path({tests!r})          # do not put the source checkout on sys.path
binding = adapter.install()
host = fake_host.FakeHost(); host.bind(); host.register(binding)
import pythonx.compose.ui.graphics as graphics
assert "site-packages" in graphics.__file__, graphics.__file__
white = graphics.Color(0xFFFFFFFF)       # held: dropping a proxy releases its handle
red = graphics.Color.Red
assert host._object(white._pm_handle).label == "Color(0xffffffff)"
assert host._object(red._pm_handle).label == "Red"
print("installed wheel ok")
"""


class TheWheel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        for needed in ("setuptools", "wheel"):
            if importlib.util.find_spec(needed) is None:
                raise unittest.SkipTest(f"{needed} is not installed; the wheel cannot be built here")
        SCRATCH.mkdir(exist_ok=True)
        cls._dir = tempfile.TemporaryDirectory(dir=SCRATCH)
        wheel = _build_wheel(Path(cls._dir.name))
        cls.wheel = wheel
        with zipfile.ZipFile(wheel) as archive:
            cls.names = set(archive.namelist())

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def test_the_manifest_is_inside_the_package(self):
        self.assertIn("pythonx/compose/pythonx-map.toml", self.names)

    def test_every_mapped_module_is_a_file_in_the_wheel(self):
        with (REPO / "pythonx" / "compose" / "pythonx-map.toml").open("rb") as handle:
            modules = tomllib.load(handle)["modules"]
        missing = sorted(
            name for name in modules
            if name.replace(".", "/") + "/__init__.py" not in self.names
        )
        self.assertEqual([], missing, "a mapped module with no file cannot be imported once installed")

    def test_no_build_tooling_or_tests_ship(self):
        for prefix in ("scripts/", "tests/", "docs/", ".github/"):
            with self.subTest(prefix=prefix):
                self.assertEqual([], sorted(n for n in self.names if n.startswith(prefix)))

    def test_the_re_export_rule_ships(self):
        self.assertIn("pythonx/compose/_reexport.py", self.names)

    def test_the_package_is_marked_typed(self):
        self.assertIn("pythonx/compose/py.typed", self.names)

    def test_the_generated_stubs_ship(self):
        for stub in ("pythonx/compose/ui/__init__.pyi", "pythonx/compose/layout/__init__.pyi"):
            with self.subTest(stub=stub):
                self.assertIn(stub, self.names)

    def test_color_is_callable_from_the_installed_wheel(self):
        """Issue #88: the installed package, not the source tree, calls `Color(0xFFFFFFFF)` through the binder."""
        sys.path.insert(0, str(REPO / "tests"))
        try:
            import adapter
            home = adapter.python_multiplatform_home()
        finally:
            sys.path.pop(0)
        if not (home / adapter._ADAPTER_KT).is_file():
            self.skipTest("no python-multiplatform checkout to install the binder from")
        venv = Path(self._dir.name) / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        python = venv / "bin" / "python"
        subprocess.run([str(python), "-m", "pip", "install", "-q", "--no-deps", "--no-index", str(self.wheel)],
                       check=True, capture_output=True, text=True)
        script = _SCENARIO.format(tests=str(REPO / "tests"))
        env = dict(os.environ, PYTHONMULTIPLATFORM_HOME=str(home))
        result = subprocess.run([str(python), "-c", script], capture_output=True, text=True, env=env,
                                cwd=str(venv))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("installed wheel ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
