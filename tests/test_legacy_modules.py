"""Tests verifying that legacy Chaquopy/JPype code and dead relative imports are removed from remaining pythonx modules.

Covers:
- `pythonx/compose/layout/__init__.py`
- `pythonx/compose/lite/app.py`, `jvm.py`, `material3.py`, `runtime.py`
- `pythonx/compose/test/main.py`
- `pythonx/compose/ui/unit/__init__.py` and `pythonx/compose/ui/unit/dp.py`
- `pythonx/compose/material3/__init__.py`
"""

from __future__ import annotations

import ast
import importlib.util
import io
import tokenize
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

LAYOUT_INIT = REPO / "pythonx" / "compose" / "layout" / "__init__.py"
LITE_DIR = REPO / "pythonx" / "compose" / "lite"
TEST_MAIN = REPO / "pythonx" / "compose" / "test" / "main.py"
UI_UNIT_INIT = REPO / "pythonx" / "compose" / "ui" / "unit" / "__init__.py"
UI_UNIT_DP = REPO / "pythonx" / "compose" / "ui" / "unit" / "dp.py"
MATERIAL3_INIT = REPO / "pythonx" / "compose" / "material3" / "__init__.py"


def _get_executable_tokens(path: Path) -> set[str]:
    """Tokenize a file, stripping comments and string literals, returning all remaining token strings."""
    if not path.exists():
        return set()
    raw = path.read_text(encoding="utf-8")
    kept = []
    for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            continue
        kept.append(tok.string)
    return set(kept)


class TestLayoutInitModuleNoDeadTokens(unittest.TestCase):
    def test_layout_init_has_no_dead_relative_imports_or_chaquopy_tokens(self) -> None:
        tokens = _get_executable_tokens(LAYOUT_INIT)
        for banned in ("Arrangement", "arrangement", "traceback"):
            self.assertNotIn(
                banned,
                tokens,
                f"pythonx/compose/layout/__init__.py still contains dead token: {banned}",
            )


class TestLiteModulesNoDeadTokens(unittest.TestCase):
    def test_lite_modules_have_no_jpype_or_chaquopy_tokens(self) -> None:
        lite_files = {
            "app.py": LITE_DIR / "app.py",
            "jvm.py": LITE_DIR / "jvm.py",
            "material3.py": LITE_DIR / "material3.py",
            "runtime.py": LITE_DIR / "runtime.py",
        }
        banned_tokens = {
            "jpype", "windll", "AppKt", "Material3Kt", "PlatformKt",
            "SimpleTextWidget", "SimpleSpacer", "SimpleCardWidget", "SimpleButtonWidget",
        }
        for filename, path in lite_files.items():
            tokens = _get_executable_tokens(path)
            for banned in banned_tokens:
                self.assertNotIn(
                    banned,
                    tokens,
                    f"pythonx/compose/lite/{filename} still contains legacy token: {banned}",
                )


class TestTestMainModuleNoDeadTokens(unittest.TestCase):
    def test_test_main_has_no_legacy_demo_tokens(self) -> None:
        tokens = _get_executable_tokens(TEST_MAIN)
        for banned in ("SimpleText", "SimpleColumn", "SimpleRow", "SimpleButton", "ComposeApp", "EmptyComposable"):
            self.assertNotIn(
                banned,
                tokens,
                f"pythonx/compose/test/main.py still contains dead token: {banned}",
            )


class TestUiUnitInitNoDeadTokens(unittest.TestCase):
    def test_ui_unit_init_has_no_dead_relative_import_tokens(self) -> None:
        tokens = _get_executable_tokens(UI_UNIT_INIT)
        self.assertNotIn(
            "dp",
            tokens,
            "pythonx/compose/ui/unit/__init__.py still contains dead relative import of dp.py",
        )


class TestMaterial3InitNoPlaceholderStarImports(unittest.TestCase):
    def test_material3_init_has_no_dead_star_imports_of_placeholder_files(self) -> None:
        tokens = _get_executable_tokens(MATERIAL3_INIT)
        for banned in (
            "bottom_app_bar", "bottom_sheet", "checkbox", "date_picker", "dialogs",
            "dividers", "extended_fab", "fab", "menus", "navigation_bar", "navigation_drawer",
            "navigation_rail", "progress_indicators", "radio_button", "search_bar",
            "segmented_button", "sliders", "snackbars", "swipe_to_dismiss", "switch",
            "tabs", "time_picker", "tool_tip", "top_app_bar", "surfaces", "scaffold",
            "dynamic_color", "typography", "shape",
        ):
            self.assertNotIn(
                banned,
                tokens,
                f"pythonx/compose/material3/__init__.py still imports 0-byte placeholder module: {banned}",
            )


class TestRetiredModulesExposeTheirExplanationAsADocstring(unittest.TestCase):
    """
    These files exist to be read. Their whole content is an explanation of what used to be here,
    where those names come from now, and how they have to be spelled -- so the explanation has to
    reach `help()` and `__doc__`, not merely sit in the file.

    It did not. Twelve of them opened with `from __future__ import annotations` above the string,
    which makes the string an expression statement rather than a docstring: `ast.get_docstring`
    returned `None` for every one, and `help(module)` showed nothing. The import bought nothing
    either -- none of these modules has an annotation to postpone. This pins the outcome rather
    than the cause, so any future way of losing the docstring fails here too.
    """

    RETIRED = (
        "pythonx/compose/ui/alignment.py",
        "pythonx/compose/ui/unit/dp.py",
        "pythonx/compose/ui/unit/__init__.py",
        "pythonx/compose/test/main.py",
        "pythonx/compose/lite/material3.py",
        "pythonx/compose/lite/runtime.py",
        "pythonx/compose/lite/app.py",
        "pythonx/compose/lite/jvm.py",
        "pythonx/compose/layout/arrangement.py",
        "pythonx/compose/layout/__init__.py",
    )

    def test_each_retired_module_has_a_real_docstring(self) -> None:
        for relative in self.RETIRED:
            path = REPO / relative
            with self.subTest(module=relative):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                doc = ast.get_docstring(tree)
                self.assertIsNotNone(
                    doc,
                    f"{relative}'s explanation is not a docstring -- check for a statement above it",
                )
                self.assertGreater(len(doc.strip()), 40, f"{relative}'s docstring says almost nothing")


if __name__ == "__main__":
    unittest.main()
