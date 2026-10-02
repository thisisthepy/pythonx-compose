# `icon.py` and `color_scheme.py` are records, not part of this package's surface, and are not
# imported here. Star-importing them made `import pythonx.compose.material3` import
# `androidx.compose.material3` at load time -- failing wherever that Kotlin package is not bound --
# and put their dead `Icon` / `ColorScheme` classes in front of the binder's real ones, which the
# re-export rule below serves. Whether the two files stay is an open question (SPEC, Outside intent 5).


# `Text` is not here. `pythonx.compose.material3.Text` is a walked declaration -- the adaptation
# layer builds it from the artefact table, the same way `pythonx.compose.ui.Modifier.padding` is
# built and not hand-written (`pythonx/compose/ui/modifier.py`). A per-declaration `text.py` used to
# be imported here; it duplicated what the layer already does and could not be repaired (it looked
# `Text-<mangled>` up by a name-prefix search Kotlin's value-class mangling makes impossible -- see
# `modifier.py`'s module docstring for why). `tests/test_material3_module.py` is what checks this.
#
# `Button`, `Card`, `ListItem`, `Badge`/`BadgedBox` and `MaterialTheme` are not here either, for the
# same reason and on the same evidence shape: `PythonMultiplatform` commit `a6742a1c`
# (`ComposableRenderTest.kt`) renders each of them from Python with no wrapper at all, content
# lambda and (where present) `on_click` included, against the real `material3` jar --
#
#   buttonComposesItsClickHandlerAndItsRowScopedContent    -> buttons.py            (Button et al.)
#   cardResolvesToTheNonClickableOverloadAndDrawsItsContent -> cards.py             (Card et al.)
#   listItemComposesItsHeadlineContentUnderItsSnakeCasedName -> lists.py            (ListItem)
#   badgeDrawsItsLeafFormWithNoArgumentsAndMoreWithContent  -> badge.py             (Badge)
#   badgedBoxComposesBothItsBadgeAndItsContentScopes        -> badge.py             (BadgedBox)
#   materialThemeComposesAZeroArgumentContentLambda         -> material_theming.py  (MaterialTheme)
#
# Each of those files was a copy of the same `__COMPILED_CODE__` / `find_composable` /
# `name.startswith("<Name>-")` template `text.py` and `modifier.py` used -- the sibling declarations
# in each file (`ElevatedButton`, `OutlinedCard`, ...) were never individually rendered, but they are
# the identical template with only the `*Kt` attribute name changed, so the one proof per file is the
# same class of evidence the `Text` deletion already established: the template is dead, not the
# specific name. `tests/test_material3_module.py` asserts each file is gone.
#
# `icon_button.py` is now gone entirely, not just half. `IconButton` and its plain siblings already
# had the render proof (`iconButtonComposesItsClickHandlerAndItsContent`, `a6742a1c`). The
# `IconToggleButton` family (`checked: Boolean`, `onCheckedChange: (Boolean) -> Unit`) needed a
# different shape of proof -- a static render delivers no events, so nothing about a callback slot
# could be shown by rasterising -- and `PythonMultiplatform` commit `3fde8bd6`
# (`CallbackDrivenRenderTest.kt`) supplies it: a real pointer press and release through
# `ImageComposeScene.sendPointerEvent`, asserted to invoke the Python callback with the value Compose
# handed it, on **two** declarations deliberately (`Checkbox` in `CheckboxKt`, then `Switch` in
# `SwitchKt`, specifically to rule out a mechanism that only happens to work for one file). The
# `IconToggleButton` family is a third declaration, in a third file (`IconButtonKt`), with that exact
# same `(Boolean) -> Unit` shape -- the same class of generalisation this module already applies
# within a single file for `Button`'s and `IconButton`'s untested siblings, extended here across
# files because the render test itself was built to cross that boundary.
#
# `text_field.py` is now gone too. `on_value_change` is `(String) -> Unit` -- a shape
# `CallbackDrivenRenderTest.kt` did not used to drive, only `(Boolean) -> Unit` -- so it stayed
# hand-written after `icon_button.py` went. `PythonMultiplatform` commit `cac8243f` closes that gap:
# `typingIntoATextFieldInvokesThePythonCallbackWithTheStringAndTheNextRenderShowsIt` types a real key
# event into a `pythonx`-bound `TextField`, asserts the Python callback received the string, and
# asserts a fresh render shows it; `twoKeystrokesAccumulateAcrossTwoFreshScenes` repeats it across two
# scenes to show the string accumulates rather than just landing once. Same bar the toggle buttons
# met, same conclusion. `tests/test_material3_module.py` is what checks all of this.
#
# `icon.py` and `color_scheme.py` do **not** get the same conclusion, and are not going anywhere:
# `PythonMultiplatform` commit `a6742a1c` pinned `Icon`, `lightColorScheme` and `darkColorScheme` as
# *unreachable* through the walked table -- `Icon` needs an `ImageBitmap`/`ImageVector`/`Painter`
# nothing walked can produce, and the two color-scheme factories need 36 `Color` parameters against a
# 6-parameter omission cap -- which is a stronger, opposite finding from the one that deleted
# `text.py`/`icon_button.py`/`text_field.py` (those were proven *redundant*; these were proven
# *uncallable any way at all*). The hand-written wrapper is the only Python-facing record of that, so
# it stays. What it no longer does is subclass `pythonx.compose.runtime.Composable`: `7d6c0a1`
# replaced that name's 2024 *class* with a plain identity-decorator *function*, and a function cannot
# be a base class -- `class Icon(Composable):` raised `TypeError` the moment this package was
# imported, which broke every other, working declaration in this package along with it, not just the
# two that are genuinely unreachable. Both classes are now defined plain, without a base, so importing
# this package no longer depends on two declarations that can never be called anyway. Calling either
# still fails (`self.composer` is never set -- nothing sets it, because the composer-threading base
# class it depended on is exactly what `7d6c0a1` retired), which is accurate: neither declaration
# works, before or after this fix. `tests/test_material3_module.py` checks the import no longer
# raises.
#
# `checkbox.py` and `switch.py` are not files in the sense any of the above are: both have been
# empty since before this package had an adaptation layer to defer to (`git log -p` on either shows
# no non-empty version). `Checkbox`/`Switch` reach Python entirely through the walked table -- which
# is exactly what `CallbackDrivenRenderTest.kt` exercises above -- and the empty files cost nothing
# and assert nothing; they are left as they are rather than deleted, so as not to conflate "always
# empty" with "emptied on evidence" in the file history.

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
