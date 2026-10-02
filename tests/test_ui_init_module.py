"""`pythonx/compose/ui/__init__.py` -- the file `import pythonx.compose.ui` loads, and what it no longer contains.

Two things are asserted here:
1. That `import pythonx.compose.ui`, with the binder installed, loads the file on disk, while the
   binder serves the Kotlin name `androidx.compose.ui` as a separate module.
2. That no dead Chaquopy-era code (`jclass`, `from .modifier import Modifier`, etc.) survives in
   executable tokens in `pythonx/compose/ui/__init__.py`.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tokenize
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
UI_INIT_PY = REPO / "pythonx" / "compose" / "ui" / "__init__.py"


class TheUiInitModuleIsTheFileOnDisk(unittest.TestCase):
    """`import pythonx.compose.ui` loads `pythonx/compose/ui/__init__.py`, with the binder installed."""

    def setUp(self):
        try:
            self.binding = adapter_loader.install()
        except adapter_loader.AdapterUnavailable as unavailable:
            self.skipTest(str(unavailable))
        self.host = fake_host.FakeHost()
        self.host.bind()
        self.host.register(self.binding)
        self.addCleanup(self.host.unbind)
        self.addCleanup(adapter_loader.uninstall)

    def test_import_pythonx_compose_ui_loads_the_file_on_disk(self):
        import pythonx.compose.ui as ui

        self.assertEqual(UI_INIT_PY, Path(ui.__file__).resolve())

    def test_the_binder_serves_the_kotlin_name_not_pythonx(self):
        import androidx.compose.ui as kotlin_ui
        import pythonx.compose.ui as ui

        self.assertFalse(hasattr(kotlin_ui, "__file__"), "androidx.compose.ui is the binder's module")
        self.assertIsNot(ui, kotlin_ui)


class TheChaquopyUiInitMechanismIsGone(unittest.TestCase):
    """No `jclass`, no relative imports `from .modifier import Modifier` in `ui/__init__.py`."""

    def setUp(self):
        raw = UI_INIT_PY.read_text(encoding="utf-8")
        kept = []
        for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                continue
            kept.append(tok.string)
        self.tokens = set(kept)

    def test_no_chaquopy_or_relative_import_tokens_survive(self):
        for banned in ("jclass", "modifier", "alignment", "AbsoluteAlignment"):
            self.assertNotIn(
                banned,
                self.tokens,
                f"{banned} is dead Chaquopy-era code or invalid relative import in ui/__init__.py",
            )


if __name__ == "__main__":
    unittest.main()
