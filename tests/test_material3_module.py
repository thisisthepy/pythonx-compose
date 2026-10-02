"""`pythonx/compose/material3/` -- which per-declaration wrappers the adaptation layer already covers.

`Text` is the one this asserts, and only this one: `docs/...` (`ComposableRenderTest.kt`,
`PythonMultiplatform` commit `c60bcfeb`) proved `from pythonx.compose.material3 import Text;
Text('hi')` draws real pixels through the walked `material3` jar with **no Python wrapper at all** --
the same shape `test_modifier_module.py` proved for `Modifier.padding`. `pythonx/compose/material3/
text.py` predates that: it imports `androidx.compose.material3.TextKt` directly (a mechanism this
tree no longer has) and, on the way in, does the exact `name.startswith("Text-")` mangled-suffix
search `test_modifier_module.TheShellIsGone` already bans for `Modifier` -- the same impossible
search, since Kotlin's value-class mangling suffix hashes the signature and not the name. It cannot
be repaired; it can only be removed, the way `modifier.py`'s copy of it was.

Nothing here proves Compose still renders `Text` -- that is `ComposableRenderTest.kt`'s job, in the
other repository, and it needs a JVM this repository does not have. What this checks is local: that
the dead wrapper is gone and nothing in this repository still points at it.

`Icon`, `ColorScheme`, `lightColorScheme` and `darkColorScheme` are the same shape (`TextKt` /
`IconKt` / `ColorSchemeKt` imports, the same mangled-suffix search) but nothing has independently
confirmed them walked and rendering the way `Text` is confirmed -- so they are left alone here rather
than asserted dead on architecture alone. `docs/` and the migration report list them as the same
class of finding, unconfirmed.

`Button`, `Card`, `ListItem`, `Badge`/`BadgedBox`, `MaterialTheme` and (half of) `IconButton` are the
same shape again, on `PythonMultiplatform` commit `a6742a1c` (`ComposableRenderTest.kt`): each renders
from Python with no wrapper, content lambda and `on_click` included where the declaration has one.

`icon_button.py` is now gone entirely. `PythonMultiplatform` commit `3fde8bd6`
(`CallbackDrivenRenderTest.kt`) is the render proof the previous version of this module's docstring
said was missing: it drives `Checkbox`'s `onCheckedChange` with a real pointer press and release
through `ImageComposeScene.sendPointerEvent` -- no window, no display -- and asserts the Python
callback ran with the value Compose handed it (`_cb_events == [True]`) and that a fresh render shows
the state it wrote. `theSameCallbackShapeIsDrivenOnASecondDeclaration` repeats it on `Switch`,
deliberately: a different file (`SwitchKt` vs `CheckboxKt`), a different declaration, the identical
`(Boolean) -> Unit` shape, written specifically to rule out "a lucky slot index that only happens to
work for `Checkbox`". `IconToggleButton`/`FilledIconToggleButton`/`FilledTonalIconToggleButton`/
`OutlinedIconToggleButton` are a *third* declaration (`IconButtonKt`, a third file again) with that
same shape and the same parameter names (`checked: Boolean`, `onCheckedChange: (Boolean) -> Unit`) --
the evidence the render test was built to generalise across declaration boundaries applies to them
for the same reason it already covers two unrelated files. So the four toggle classes are deleted the
same way `IconButton`'s plain siblings were.

`text_field.py`'s `TextField`/`OutlinedTextField` were the one case the callback-shape
generalisation above could not reach: `on_value_change` is `(String) -> Unit`, not
`(Boolean) -> Unit`, and `CallbackDrivenRenderTest.kt` used to drive only the Boolean shape. That gap
is closed now. `PythonMultiplatform` commit `cac8243f`
(`typingIntoATextFieldInvokesThePythonCallbackWithTheStringAndTheNextRenderShowsIt` and
`twoKeystrokesAccumulateAcrossTwoFreshScenes`, both in `CallbackDrivenRenderTest.kt`) delivers real
key events through `ImageComposeScene.sendKeyEvent` to a `pythonx`-bound `TextField`, asserts the
Python callback received the typed string, and asserts a fresh render shows it -- then repeats that
across two scenes to show the string *accumulates* (`'h'` then `'hi'`), not just that one keystroke
lands. That is the same evidentiary bar the `(Boolean) -> Unit` shape met for `Checkbox`/`Switch`,
now met for `(String) -> Unit`, so `text_field.py` is gone the same way `icon_button.py` was.

Nothing here proves Compose still renders `IconToggleButton` or `TextField` when it composes for
real -- that render-with-real-Compose claim is what `CallbackDrivenRenderTest.kt` supplies, in the
other repository. What this file checks is local: that the dead wrapper is gone and nothing in this
repository still points at it, the same thing it already checked for `Text` and for `Button`'s
siblings.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MATERIAL3_DIR = REPO / "pythonx" / "compose" / "material3"
MATERIAL3_INIT = MATERIAL3_DIR / "__init__.py"


def _load_by_path(path: Path, name: str) -> types.ModuleType:
    """Load a `pythonx/...` file directly, the same way `test_modifier_module.py` and
    `test_runtime_module.py` do (`pythonx` has no real filesystem path once the host's adapter has
    installed a synthetic one, so tests read the file off disk instead).
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheTextWrapperIsGone(unittest.TestCase):
    """`Text` needs no Python: `pythonx.compose.material3.Text` is a walked declaration."""

    def test_text_module_does_not_exist(self):
        self.assertFalse(
            (MATERIAL3_DIR / "text.py").exists(),
            "text.py is a per-declaration wrapper the adaptation layer already covers "
            "(PythonMultiplatform commit c60bcfeb renders Text('hi') with none)",
        )

    def test_material3_package_does_not_import_a_text_module(self):
        # Substring guard: `.text` is the exact submodule this test is about. (`text_field.py` used
        # to need the same care -- it was a real, still-pending wrapper -- but `TheTextFieldWrapperIsGone`
        # now asserts it is deleted outright, so there is no longer a `.text`-prefixed sibling to
        # avoid colliding with.)
        source = MATERIAL3_INIT.read_text(encoding="utf-8")
        self.assertNotIn("from .text import", source)


class TheRenderProvenWrappersAreGone(unittest.TestCase):
    """Each of these files was the same `text.py`/`modifier.py` template: `__COMPILED_CODE__`,
    `find_composable`, and a `name.startswith("<Name>-")` mangled-suffix search over `*Kt.__dict__`.
    `PythonMultiplatform` commit `a6742a1c` (`ComposableRenderTest.kt`) rendered one declaration per
    file from Python with no wrapper at all, which is the same evidence `Text` had -- so the whole
    file goes, the same way `text.py` did.
    """

    # module filename -> (render test that proved it, declaration(s) it proves)
    PROVEN_FILES = {
        "buttons.py": (
            "buttonComposesItsClickHandlerAndItsRowScopedContent", "Button"
        ),
        "cards.py": (
            "cardResolvesToTheNonClickableOverloadAndDrawsItsContent", "Card"
        ),
        "lists.py": (
            "listItemComposesItsHeadlineContentUnderItsSnakeCasedName", "ListItem"
        ),
        "badge.py": (
            "badgeDrawsItsLeafFormWithNoArgumentsAndMoreWithContent / "
            "badgedBoxComposesBothItsBadgeAndItsContentScopes", "Badge, BadgedBox"
        ),
        "material_theming.py": (
            "materialThemeComposesAZeroArgumentContentLambda", "MaterialTheme"
        ),
    }

    def test_proven_wrapper_files_do_not_exist(self):
        for filename, (test_name, decl) in self.PROVEN_FILES.items():
            self.assertFalse(
                (MATERIAL3_DIR / filename).exists(),
                f"{filename} wraps {decl}, which {test_name} already proves the adaptation layer "
                "renders with no Python wrapper (PythonMultiplatform commit a6742a1c)",
            )

    def test_material3_package_does_not_import_the_deleted_modules(self):
        source = MATERIAL3_INIT.read_text(encoding="utf-8")
        for filename in self.PROVEN_FILES:
            module = filename[:-3]  # strip ".py"
            self.assertNotIn(
                f"from .{module} import", source,
                f"__init__.py still imports the deleted {filename}",
            )


class TheIconButtonModuleIsEntirelyGone(unittest.TestCase):
    """`IconButton` and its plain siblings had the same render proof as `Button`
    (`iconButtonComposesItsClickHandlerAndItsContent`, commit `a6742a1c`) and were already deleted
    here. The toggle variants (`IconToggleButton`, `FilledIconToggleButton`,
    `FilledTonalIconToggleButton`, `OutlinedIconToggleButton`) are gone too now: `PythonMultiplatform`
    commit `3fde8bd6` (`CallbackDrivenRenderTest.kt`) proves the `(Boolean) -> Unit` callback shape
    they share with `Checkbox`/`Switch` is driven end to end by a real pointer event on two unrelated
    declarations, and the toggle buttons are a third declaration with the identical shape. With both
    halves proven, the whole file is redundant -- the same conclusion `text.py`'s deletion reached for
    a single declaration, reached here for all four.
    """

    def test_icon_button_module_does_not_exist(self):
        self.assertFalse(
            (MATERIAL3_DIR / "icon_button.py").exists(),
            "icon_button.py wrapped IconButton (already render-proven, a6742a1c) and the "
            "IconToggleButton family, whose (Boolean) -> Unit callback shape is now render-proven "
            "on two other declarations (3fde8bd6, CallbackDrivenRenderTest.kt)",
        )

    def test_material3_package_does_not_import_icon_button(self):
        source = MATERIAL3_INIT.read_text(encoding="utf-8")
        self.assertNotIn("from .icon_button import", source)


class TheTextFieldWrapperIsGone(unittest.TestCase):
    """`text_field.py` wrapped `TextField`/`OutlinedTextField`, whose `on_value_change` is
    `(String) -> Unit`. `PythonMultiplatform` commit `cac8243f`
    (`CallbackDrivenRenderTest.kt`'s `typingIntoATextFieldInvokesThePythonCallbackWithTheStringAndTheNextRenderShowsIt`
    and `twoKeystrokesAccumulateAcrossTwoFreshScenes`) drives that exact shape end to end -- real key
    events, a Python callback receiving the typed string, a fresh render showing it, and the string
    accumulating across scenes -- the same bar `3fde8bd6` met for `(Boolean) -> Unit` on
    `Checkbox`/`Switch` before `icon_button.py` was deleted on it. With that proof in hand the
    hand-written wrapper is redundant the same way, so it is deleted the same way.
    """

    def test_text_field_module_does_not_exist(self):
        self.assertFalse(
            (MATERIAL3_DIR / "text_field.py").exists(),
            "text_field.py wrapped TextField/OutlinedTextField, whose (String) -> Unit callback is "
            "now render-proven end to end (PythonMultiplatform commit cac8243f, "
            "CallbackDrivenRenderTest.kt)",
        )

    def test_material3_package_does_not_import_text_field(self):
        source = MATERIAL3_INIT.read_text(encoding="utf-8")
        self.assertNotIn("from .text_field import", source)


class ThePackageDoesNotImportTheRecords(unittest.TestCase):
    """`icon.py` / `color_scheme.py` are not imported by the package, so they shadow nothing.

    Star-importing them made `import pythonx.compose.material3` reach for `androidx.compose.material3`
    at load time and put a dead `Icon` class in front of the one the re-export rule serves.
    """

    def test_the_package_init_does_not_import_them(self):
        source = MATERIAL3_INIT.read_text(encoding="utf-8")
        self.assertNotIn("from .icon import", source)
        self.assertNotIn("from .color_scheme import", source)

    def test_the_package_imports_with_no_binder_installed(self):
        import importlib
        import sys

        for name in [n for n in sys.modules if n == "pythonx.compose.material3" or n.startswith("androidx")]:
            del sys.modules[name]
        sys.path.insert(0, str(REPO))
        try:
            module = importlib.import_module("pythonx.compose.material3")
        finally:
            sys.path.remove(str(REPO))
        self.assertNotIn("Icon", vars(module))


class TheTwoUnreachableWrappersLoadWithoutCrashing(unittest.TestCase):
    """`icon.py` (`Icon`) and `color_scheme.py` (`ColorScheme`/`lightColorScheme`/`darkColorScheme`)
    are the two declarations `PythonMultiplatform` commit `a6742a1c` pinned as *unreachable* through
    the walked table, not merely unconfirmed: `Icon` needs an `ImageBitmap`/`ImageVector`/`Painter`
    nothing walked can produce, and the two color-scheme factories need 36 `Color` parameters against
    the binding's 6-parameter omission cap. "Pinned unreachable" is a different conclusion from the
    evidence that deleted `text.py`, `icon_button.py` and now `text_field.py`: those were proven
    *redundant* (the walked table draws the same declaration with no wrapper), so the wrapper could
    go. `Icon`/`ColorScheme` were proven *uncallable any way at all*, which makes the hand-written
    wrapper the only Python-facing record of that fact -- so `text_field.py`'s reasoning does not
    apply and these two files stay, per this task's own instruction.

    Both files still wrote the 2024 shape, `class Icon(Composable):` /
    `class ColorScheme(Composable):`, inheriting from `pythonx.compose.runtime.Composable`. Commit
    `7d6c0a1` replaced that name's *class* with a plain identity-decorator *function* -- correct for
    `UI.ipynb`'s `@Composable def Screen(): ...` usage, but a function cannot be a base class, so the
    `class` statement itself now raises `TypeError` the moment either file is loaded. Because
    `pythonx/compose/material3/__init__.py` imports both unconditionally (`from .icon import *`,
    `from .color_scheme import *`), that `TypeError` previously took down `import
    pythonx.compose.material3` as a whole -- every other, working declaration (`Button`, `Card`,
    `Text`, ...) included, not just the two that are genuinely unreachable. That is the regression
    this class checks is fixed: loading each file must not raise, which it can satisfy without
    claiming `Icon`/`ColorScheme` now render (they still cannot -- see the class docstrings in each
    file) by simply not inheriting from something that is no longer a class.
    """

    def setUp(self):
        # `androidx` is not installed in this pure-Python checkout (`docs/pythonx-adapter-design.md`
        # explains why: the real binding lives across a JVM/native boundary this repository's test
        # suite has no access to). Both files only *reference* a handful of attributes off
        # `androidx.compose.material3` at module scope and never call anything on them at import
        # time, so a bare stand-in that has those attributes is enough to reach the `class` statement
        # this test is actually about.
        stub = types.ModuleType("androidx.compose.material3")
        stub.IconKt = object()
        stub.ColorSchemeKt = object()
        stub.ColorScheme = object()
        self._previous = {
            name: sys.modules.get(name)
            for name in ("androidx", "androidx.compose", "androidx.compose.material3")
        }
        sys.modules["androidx"] = types.ModuleType("androidx")
        sys.modules["androidx.compose"] = types.ModuleType("androidx.compose")
        sys.modules["androidx.compose.material3"] = stub
        self.addCleanup(self._restore_androidx)

    def _restore_androidx(self):
        for name, previous in self._previous.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous

    def test_icon_module_loads_without_raising(self):
        module = _load_by_path(MATERIAL3_DIR / "icon.py", "_test_material3_icon")
        self.assertTrue(hasattr(module, "Icon"))

    def test_color_scheme_module_loads_without_raising(self):
        module = _load_by_path(MATERIAL3_DIR / "color_scheme.py", "_test_material3_color_scheme")
        self.assertTrue(hasattr(module, "ColorScheme"))
        self.assertTrue(hasattr(module, "lightColorScheme"))
        self.assertTrue(hasattr(module, "darkColorScheme"))

    def test_neither_file_inherits_from_the_now_functional_composable(self):
        for filename in ("icon.py", "color_scheme.py"):
            source = (MATERIAL3_DIR / filename).read_text(encoding="utf-8")
            self.assertNotIn(
                "(Composable)", source,
                f"{filename} still subclasses Composable, which 7d6c0a1 made a plain function -- "
                "that raises TypeError the moment the class statement runs",
            )


if __name__ == "__main__":
    unittest.main()
