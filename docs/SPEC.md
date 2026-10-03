# Specification

What `pythonx-compose` does: the behavioural contract. Every item stays inside `docs/INTENT.md`;
anything found in the repository that INTENT does not cover is listed at the end under
**Outside intent: needs a decision** rather than written into the contract.

Each item carries a status:

| Status | Meaning |
|---|---|
| `implemented` | Behaviour exists in this repository **and** a test in `tests/` that was read for this document exercises it and passes. |
| `partial` | Some of it exists, or it exists but its tests do not currently pass, or its only evidence is outside this repository. |
| `planned` | Required by INTENT; nothing in this repository delivers it yet. |

A behaviour change starts here, then becomes a failing test, then code (`AGENTS.md` §5).

## 0. Test baseline (2026-10-03, after the a5028618 stubs)

Run from a worktree with `uv run --with pytest --with mypy pytest tests -q -rs` (pytest 8, mypy 2.4, CPython 3.13), where
`UI.ipynb` is absent and its one test skips:

| Environment | Result |
|---|---|
| No `PythonMultiplatform` checkout found | **148 passed, 113 skipped**, 167 subtests passed |
| python-multiplatform `develop` at `31c092f0` or later (property rows, #38; `describe_member`, #54; besides `add_member_resolver` and `describe(module, name)`) | **260 passed, 1 skipped**, 198 subtests passed |
| an older checkout, before python-multiplatform #131 (no binder-side snake_case names) | the same, with the snake_case method tests skipped |
| an older one, without `describe(module, name)` (python-multiplatform #36) | with 13 more skipped again |
| an older one still, without `add_member_resolver` | with 5 more skipped again |

Measured in a worktree, which has `.tmp/kotlin-stubs.zip` but no `UI.ipynb`. Without a checkout, the
112 tests that install the binder's layers through `tests/adapter.py` skip (one of them against the
installed wheel, #88), plus the notebook test.
Against a binder without `describe(module, name)`, the 13 that check grouped constants (§7, S7.1)
skip. Against a binder before python-multiplatform #131, the tests that call a snake_case method or
pass a snake_case keyword on a proxy the binder returned skip, because those names are the binder's. The skip against a current checkout is `UI.ipynb`'s (§2). A binder older than #38 skips the 5
`TheBinderPath` tests (S5.4). A binder without the `@Composable` binding (`push_composer`) skips the 13 text-field tests (S5.5). `tests/test_typing.py` skips where mypy is not installed. A skip is not a
pass.

Of the 148 that pass without a checkout, 73 check the type stubs and the wheel (S1.2); most of the
rest assert **absence** (a retired token, a deleted file, a docstring that exists). Those are listed
in §9 and are not counted as features.

---

## 1. Distribution

### S1.1 Installed as `pythonx-compose`, importing `pythonx.compose`: `implemented`

`pyproject.toml` declares `name = "pythonx-compose"`, version `0.1.0a2`, setuptools build,
`requires-python >= 3.11` (the runtime reads the manifest with `tomllib`), and
`packages.find include = ["pythonx.compose*"]`.

- Shipped and tested: `tests/test_wheel.py` builds the wheel from a copy of the sources and finds
  `pythonx/compose/pythonx-map.toml`, the re-export rule, and an `__init__.py` for every mapped
  module (issue #13). The manifest lives inside the package directory so `package-data` carries it.
- PyPI metadata: description, `README.md` as the long description (its links are absolute, since
  pypi.org cannot resolve relative ones), `license = "Apache-2.0"` with `LICENSE` (Apache License 2.0 since the maintainer's decision of 2026-10-03; the published 0.1.0a1 carries MIT), the two authors as
  `LICENSE` names them (no emails), keywords, classifiers (Alpha, Python 3.11-3.13, Typed) and
  project URLs. `build-system.requires` is `setuptools>=77`, which understands that license form.
- **0.1.0a1 is on PyPI** (2026-10-03: pre-release `v0.1.0a1` on develop `134a641`, publish-pypi run
  37120641414; a fresh install of 0.1.0a1 from PyPI imports cleanly).
- Released by publishing a GitHub Release tagged `v<version>` (`.github/workflows/publish-pypi.yml`,
  trigger `release: published`; a bare tag push publishes nothing): the workflow checks the
  Release's tag equals `v` + the `pyproject.toml` version (`.github/scripts/check_release_version.py`,
  `tests/test_release_version.py`), builds the sdist and wheel, runs `twine check`, smoke-installs
  the wheel in a fresh venv, then uploads through PyPI trusted publishing (environment `pypi`, no
  token). Nothing is uploaded by hand.
- Typed: the wheel carries `py.typed` and the generated `.pyi` stubs (S1.2, issue #12).

### S1.2 Type stubs ship in the wheel: `implemented`

Stubs carry the Pythonic names and signatures the runtime resolves, so the name an editor completes
and the name the interpreter resolves cannot drift.

- **What is generated.** `pythonx/compose/**/__init__.pyi` for every module in `pythonx-map.toml`,
  beside its `__init__.py`, and an empty `pythonx/compose/py.typed`. The stubs are committed;
  regenerating them from the same input produces no diff.
- **From what.** python-multiplatform's CI artefact `kotlin-stubs` (workflow run 37131041879,
  commit `452cc807`, python-multiplatform #131): Kotlin-named stubs for Compose 1.11.1, one `androidx/compose/.../__init__.pyi`
  per Kotlin package. `uv run python scripts/gen_stubs.py <kotlin-stubs.zip or directory>` converts them;
  the first line of every generated stub records the artefact, run and commit it came from.
- **The rule is the runtime's** (`_reexport.py`), applied by `scripts/gen_stubs.py`:
  - a module function or constant is renamed with `python_name` (upper-case names kept, others
    snake_case, an explicit overload keeps its suffix: `padding__Dp`); its parameters are
    snake_case, except the positional-only `receiver` and anonymous `__aN` slots; keyword-only
    markers and the binder's `@overload` sets, in the binder's order, are kept;
  - a stub class keeps its name. Its extension members (`Modifier.fill_max_width`, a
    `ClassVar` of a callable `Protocol`) are renamed with `python_name`, the binder's rule since #131,
    and the protocol's `__call__` parameters are snake_case like a module function's (the receiver and
    anonymous slots keep their names), because the runtime translates a method's keywords (S4.1);
    the stubs are Pythonic-only, so a method's Kotlin keyword, which still works at run time, fails
    a type check;
  - one name per declaration. Since python-multiplatform #131 the binder's stubs name a name twice:
    a module stub carries `fill_max_width = fillMaxWidth` beside the Kotlin-named def, a proxy class
    an alias `ClassVar` or property per member, and its signature keywords are already `snake_case`
    where it has an alias. The generator drops the alias lines and the repeated member, because
    renaming the Kotlin-named declaration by the same rule yields the same name, so no Kotlin
    second name and no line such as `fill_max_width = fill_max_width` reaches the stubs;
    `python_name` and `snake_case` are idempotent on a `snake_case` name, so a keyword the binder
    already spells that way is unchanged. A name the binder declares as a callable module
    (`PaddingValues: _PaddingValues_callable_module`, whose `__call__` holds the explicit overloads
    and whose members are its constants) is that declaration, with no base-name `def` beside it;
  - a Kotlin object served as a sub-package (`Alignment`, `Arrangement`) becomes a class of that
    name in its parent module's stub, its constants `ClassVar`s and its functions snake_case
    static methods (an explicit overload set, `spaced_by__Dp`, also gets its base name `spaced_by`). A sub-package directory holding only `__init__.pyi` would be a namespace
    package at run time and would shadow the `KotlinObject` the re-export rule serves. The
    generator reads both upstream layouts: the object as its own `<Object>/__init__.pyi`, or as a
    class inside the parent stub (python-multiplatform #44). An object whose name the parent module
    also uses for a function (`Color`, `TextStyle`, `PaddingValues`, `TextUnit`) is left out,
    because at run time that name reaches the function;
  - the Kotlin types an object nests (`Alignment.Horizontal`; python-multiplatform #53, which
    declares them as classes in the object's stub) become classes nested in the object's class, and
    are the grouped-constant namespaces too (S7.1): `Alignment.End` and `Alignment.Horizontal.End`
    are both `Alignment.Horizontal`, and `Alignment.Horizontal.Top` is a type error. A reference to
    one from another module (`androidx.compose.ui.Alignment.Horizontal` in `Column`) names
    `pythonx.compose.ui.Alignment.Horizontal`. A nested type that upstream lists with several nested
    bases (`Arrangement.HorizontalOrVertical(Horizontal, Vertical)`, python-multiplatform #71) is
    typed as itself, so `Arrangement.SpaceBetween` is an `Arrangement.HorizontalOrVertical` that a
    `Column(vertical_arrangement=...)` and a `Row(horizontal_arrangement=...)` both take, and
    `Arrangement.Start` (a `Horizontal`) is a type error for a `Column`. One that lists a single
    nested base -- the first upstream format, which could not say it is both -- is still `Any`
    wherever a signature or a constant names it, decided by reading the bases and no name;
    a module function named in an explicit overload set that is also the name of a class of the same
    stub (`DpRect__Dp_Dp_Dp_Dp` beside `class DpRect`, which now carries `__init__`) gets no base-name
    overloads, the class being that name;
  - a property (`@property` with `@name.setter`, python-multiplatform #38) is renamed with
    `python_name` and so is the decorator: `layout_direction` and `@layout_direction.setter`;
  - a reference to another Kotlin package is rewritten to the `pythonx.compose` module the
    manifest lists first for it (`androidx.compose.foundation.layout` → `pythonx.compose.layout`);
    a reference to a package the manifest does not map, or to a name the target stub does not
    declare, becomes `typing.Any`;
  - a module that maps the same Kotlin package as an earlier one (`pythonx.compose.foundation.layout`)
    re-exports it (`from pythonx.compose.layout import *`), since at run time both names reach the
    same objects; `[aliases]` become re-exports too (`material3` exports `Column`, `Row`, `Spacer`
    from `pythonx.compose.layout`; a name lent under another one is assigned its path in the
    source's stub, `DefaultIcons = Icons.Default`, which upstream types as `Icons.Filled`); names a package defines itself (`runtime.Composable`) are
    carried over.
- **How it is verified.** `tests/test_stubs.py` converts five fixtures: the fake host's
  declarations in the old and the current upstream format (and the current format with an object
  in its parent stub), and a third in the format of python-multiplatform #53/#44/#38 (nested types,
  object functions, property setters), and a fourth in the format of #71/#68 (a nested type with two bases, icons as typed
  properties), and a fifth in the format of #131 (alias lines, alias members, a callable module), and checks
  the generated signatures against `inspect.signature` at run time.
  `TheCommittedStubs` regenerates from `.tmp/kotlin-stubs.zip` and requires the committed files to
  be identical (it skips where the artefact is absent, which includes CI). `tests/test_typing.py`
  runs mypy over small programs against the committed stubs: correct code passes, a misspelled
  keyword or function fails. `tests/test_wheel.py` finds `py.typed` and the stubs in the built wheel.
  Each generator step has a test that fails when the step is disabled (measured per change; see the
  commit messages of #40, #45 and the run-37103737430 regeneration for the counts).
- **What the newer input improved.** Object functions are stubbed (`Arrangement.spaced_by(8)`
  type-checks), object constants carry their nested types, an `*ItemColors` parameter is no longer
  `bool`, names that differ only in case and Python-keyword names no longer reach the stubs, and
  properties appear with their setters.
  `tests/test_typing.py` checks an object function, both spellings of a grouped constant, and a
  property assignment.
- **Still missing.**
  - Many parameter and return types are `Any`: upstream emits `Any` for a class that shares its
    name with a function (`PaddingValues`, `TextStyle`, `Color`), for packages it does not stub, and
    for an object's own type (`Alignment.Center: Alignment`, python-multiplatform's object self-type);
    `Dp` is `float`; `Arrangement.spaced_by` now returns `Arrangement.HorizontalOrVertical`. An icon is no longer `Any`: `Icons.Default` is `Icons.Filled`
    and `Icons.Filled.Add` an `ImageVector` (python-multiplatform #68), since `pythonx.compose.ui.graphics.vector`
    is mapped (S5.3). `androidx.compose.foundation.text.input` (`TextFieldState`, `rememberTextFieldState`,
    python-multiplatform #73) is not mapped, so it has no stub here: the design of the text field
    is issue #10, and a manifest row for it would emit the class with `__init__(initial_text, initial_selection)`,
    a `text` property, `set_text_and_place_cursor_at_end` and `clear_text` as `ClassVar` protocols, and
    `remember_text_field_state`.
  - The `pythonx.compose` root module maps `androidx.compose`, which has no stub, so its stub is
    empty.
  - Object constants named like a Python keyword (`FilterQuality.None`) cannot be written as an
    attribute, and are left out.
  - Regenerating needs the artefact downloaded by hand into `.tmp/`; CI does not fetch it.

## 2. The mapping manifest (`pythonx-map.toml`): `implemented`

The manifest is this package's statement of which Kotlin package each `pythonx.compose.*` module
stands for, so the binder does not have to know Compose exists (INTENT §2.3).

| Behaviour | Test |
|---|---|
| The file exists and has `[modules]` and `[value-classes]` | `tests/test_pythonx_map.py::TestManifestShipsWithThePackage::test_the_manifest_exists_and_parses` |
| Every `pythonx*` module `UI.ipynb` imports is mapped | `tests/test_pythonx_map.py::TestEveryNotebookImportIsMapped::test_the_specification_resolves` |
| `pythonx.compose.layout` → `androidx.compose.foundation.layout` (a rename no prefix rule can do) | `…::test_the_short_layout_spelling_drops_foundation` |
| `Dp` may be written as a raw number; `Color` and `TextUnit` may not | `tests/test_pythonx_map.py::TestValueClassSection::test_dp_is_allowed_and_packed_classes_are_not` |

Current mapping:

| Python module | Kotlin package |
|---|---|
| `pythonx.compose.runtime` | `androidx.compose.runtime` |
| `pythonx.compose.ui` (+ `.unit`, `.text`, `.graphics`) | `androidx.compose.ui` (+ same) |
| `pythonx.compose.layout` | `androidx.compose.foundation.layout` |
| `pythonx.compose.material3` | `androidx.compose.material3` |
| `pythonx.compose.material.icons` | `androidx.compose.material.icons` |
| `pythonx.compose.foundation.text.input` | `androidx.compose.foundation.text.input` (S5.5) |

**`[aliases]`** lends a module names from another mapped module, as data. Two forms, both under
`[aliases."<owner module>"]` keyed by the source module: a list of names lent under the **same**
name (`"pythonx.compose.layout" = ["Column", "Row", "Spacer"]`), or a table `{ lent = "Path.To.Attr" }`
that lends the attribute path under a **different** name
(`"pythonx.compose.material.icons" = { DefaultIcons = "Icons.Default" }`, INTENT §5.7). The first
segment of a path is a name of the source module; each further one is an attribute read. A name with
no dot is resolved once and kept in the owner's namespace, as before. **A path with a dot is resolved
on every read and never kept**: `Icons.Default` is a property of an object, which the binder serves
live (a `STATIC_GETTER` is never cached, python-multiplatform `_adapt`), and the alias reads as the
binder does, so `from pythonx.compose.material3 import DefaultIcons` gives the Kotlin object
`Icons.Default` gives (a new proxy for the same Kotlin object on each read). `dir()` lists every
lent name. `tests/test_pythonx_map.py::TestAliasSection` checks both forms against the manifest;
`tests/test_chain.py::DefaultIconsAlias` checks them at run time.

Caveat: `test_the_specification_resolves` reads `UI.ipynb` from the checkout it runs in. The
notebook is git-ignored, so in a worktree or CI checkout it is absent, the expected set is empty,
and **the test passes without checking anything.** It is only meaningful in the maintainer's main
checkout.

## 3. `pythonx` is a real package: `implemented` (module level)

Required by INTENT §2.2: `import pythonx.compose.material3` (and every other mapped module) loads
**this repository's files on disk**, and those files import the binder-exposed
`androidx.compose.*` modules and present them Pythonically.

Every module in `pythonx-map.toml` is a file on disk whose `__init__.py` hands its name to one rule,
`pythonx/compose/_reexport.py` (issue #8). A name read from it resolves, on first use, against the
Kotlin package the manifest maps it to: upper-case names keep their Kotlin spelling, every other
name is reached by its snake_case spelling, functions are the binder's own callables (whose
snake_case keywords and `inspect.signature` are the binder's since python-multiplatform #131), and
the manifest's value-class allowlist is handed to the binder. Names the package defines itself (`runtime.Composable`) win.

Evidence: `tests/test_runtime_module.py::TheModuleIsTheFileOnDisk`,
`tests/test_ui_init_module.py::TheUiInitModuleIsTheFileOnDisk`, and `tests/test_chain.py`
(`Names`, `Laziness`, `OverloadDispatch::test_the_module_function_dispatches_with_snake_case_keywords`,
`ValueClasses::test_the_manifest_allowlist_is_what_lets_a_number_through`), against the binder's
real Python and the fake host. Disabling the name rule fails 15 tests and the allowlist priming 12
(measured before #79 moved keyword translation into the binder).

Methods on a proxy the binder returned (`m.fill_max_width()`) and their keyword arguments
(`m.padding(padding_values=...)`) are the binder's own since python-multiplatform #131 (develop
452cc807): it serves snake_case names and keywords by this package's rule, keeps the Kotlin spelling
working, and lists Kotlin names only in `dir()`. This package no longer registers a member resolver
(issue #79). `tests/test_chain.py::TheBindersNamingRuleIsThisPackages` pins that the binder's
`python_multiplatform.python_name` and this package's agree, so the stubs and the runtime spell names
the same. The stubs are Pythonic-only (§1, S1.2), so a type checker flags a Kotlin keyword the
runtime accepts.

Division of labour since #131: the binder renames names and keywords (it never renames a namespace,
INTENT §2.3). This package keeps the module grouping (`pythonx-map.toml`), the snake-case-only
`pythonx` surface (a module lists and serves `snake_case` names only, where the binder's own
`androidx.*` serves both), the aliases, the objects and their grouped constants, the value-class
allowlist, the app root, and the Pythonic stubs. pythonx-compose needs python-multiplatform at #131 or
later for `snake_case` names and keywords on a proxy; on an older binder those calls skip in the suite.

## 4. Naming

### S4.1 Kotlin parameters, `snake_case`: `implemented`

`onClick` → `on_click`, `fillMaxWidth` → `fill_max_width`, `zIndex` → `z_index`,
`toURLString` → `to_url_string`; type names (`Modifier`) unchanged; an explicit overload keeps its
type suffix (`padding__Dp_Dp`); a name the reverse rule cannot invert still resolves, because the
rule is only ever applied forward to the module's real names; the camelCase spelling is not a second
name.

Who does it: the binder renames names and keywords since python-multiplatform #131, with this
package's rule (`pythonx.compose._reexport.python_name`, pinned equal to the binder's by
`tests/test_chain.py::TheBindersNamingRuleIsThisPackages`). This package keeps the policy that a
`pythonx` module lists and serves the `snake_case` spelling only, and the stubs name only it.

Implemented for module-level names and keywords and for method names on a binder proxy
(`tests/test_chain.py::Names`, 8 tests; `TheChain`) and for a method's keywords on a binder proxy
(`tests/test_chain.py::MethodKeywords`, 5 tests; served by the binder since python-multiplatform
#131, so they skip on an older one).

### S4.2 The notebook's spellings are examples, not the contract: `implemented` as a rule

Where `UI.ipynb` writes `onclick`, the surface is `on_click`
(`tests/test_chain.py::Names::test_on_click_not_onclick` records the decision).

## 5. Composables

### S5.1 `@Composable` decorator: `implemented`

`pythonx.compose.runtime.Composable` is an identity decorator: it returns the exact function it was
given, which still runs and keeps its name and docstring. Composer threading is not the caller's
job.

Tests: `tests/test_runtime_module.py::TheRuntimeSeam` (4 tests) and `::TheChaquopyMechanismIsGone`
(3 tests), importing `pythonx.compose.runtime` the ordinary way.

### S5.4 The app root, `app` and `state`: `partial` (the binder path is tested here against a fake host shaped after python-multiplatform #38; the real-Compose evidence is outside this repository, in the notebook E2E module)

The host draws with `PythonAppView(module = "pythonx.compose.runtime", attribute = "app_root")`
(python-multiplatform #18 and #105; issue #11). The binder owns the redraw: `PythonAppView` reads
the `app_root` State inside the composition, so a redeclared root is drawn again (seen in the
python-multiplatform #26 diagnosis). `pythonx.compose.runtime` provides:

- `app_root`: a Compose `MutableState` whose `.value` is a zero-argument callable, or `None` (the
  host draws nothing). It is created on first read, by the binder's
  `androidx.compose.runtime.mutableStateOf(None)`, because the binder may be installed after `pythonx`
  is imported; afterwards it is an ordinary module attribute, the same object every time.
- `@app`: `app(fn)` sets `app_root.value = fn` and returns `fn` unchanged. Declaring the root again
  replaces the value, so the screen follows. There is no update or refresh function (INTENT §5.1).
- `state(initial)`: `mutableStateOf(initial)`, read and written through `.value`; no `getValue` or
  `setValue`.

Both states come from one internal function, `_new_state`. When the binder cannot supply
`mutableStateOf` it raises `RuntimeError` naming python-multiplatform #38. No pure-Python state is a
fallback: it would not make Compose recompose. Names other than `app_root` still resolve through the
re-export rule, and the module's own names win.

Evidence: python-multiplatform #38 (`31c092f0`) binds generic functions and property getters and
setters, and an `Any?` slot carries a Python object as itself, so `mutableStateOf(x)` is callable and
the returned `MutableState`'s `.value` reads and writes. Since python-multiplatform #69 (PR #81) the
binder boxes a Python scalar for an `Any` slot (bool, int within 64 bits, float, str) and unboxes it
on read, so `state(0)` and `counter.value += 1` work; an int beyond 64 bits is refused with the
reason. `pythonx` does none of this itself. Tests: `tests/test_app_root.py::TheLogic` (11) and `::TheStateFactory`
(4) run against a test-only fake state patched in for `_new_state`; `::TheBinderPath` (5) uses the
real `_new_state` through the binder's Python layer and `tests/fake_host.py`, whose `mutableStateOf`
and `MutableState.value` rows are shaped after #38 (`KotlinSurface.kt`, `PythonxAdapter.kt`), not
walked from a jar. It skips against a binder older than #38. That Compose observes a write and
recomposes is not shown here. It is shown in python-multiplatform `ksp-fixtures/notebook-e2e` (#26, develop `844cf291`; 20 of 20 passed against this package's `develop` wheel on 2026-10-04, not run here, and no CI workflow runs it yet): `NotebookRootTest` declares the root, shares one state between the
notebook and the screen, and redeclares the root with `@app`, which reaches the screen within four
frames with no update call; with `@app` stubbed out, or the host handed the root once, the screen
does not change. The stub carries `app`,
`state` and `app_root` (`tests/test_stubs.py`).

### S5.2 Material 3 composables reach Python without per-widget wrappers: `partial`

`Text`, `Button`, `Card`, `ListItem`, `Badge`, `BadgedBox`, `MaterialTheme`, `IconButton` and its
toggle family, `TextField`, `Checkbox` and `Switch` are meant to be reached through the generated
`androidx.compose.material3` bindings, with no hand-written per-widget module in this package.

- In this repository: only the absence of the old wrapper files is tested
  (`tests/test_material3_module.py`, 8 tests in `TheTextWrapperIsGone`,
  `TheRenderProvenWrappersAreGone`, `TheIconButtonModuleIsEntirelyGone`, `TheTextFieldWrapperIsGone`).
- The evidence that the widgets actually render and deliver callbacks is in `python-multiplatform`
  (commits `a6742a1c`, `3fde8bd6`, `cac8243f`, cited in `pythonx/compose/material3/__init__.py`)
  and was not re-run for this document.
- `pythonx.compose.material3` re-exports `androidx.compose.material3` by the §3 rule, but the fake
  host binds no material3 declaration, so no test here exercises one.
- The render proof per widget is in python-multiplatform `ksp-fixtures/notebook-e2e` (#26, develop `844cf291`; 20 of 20 passed against this package's `develop` wheel on 2026-10-04, not run here, and no CI workflow runs it yet): `NotebookPracticeTest` (13 tests) draws `Text`,
  `Button`, `Card`, `Icon`, `Column`, `Row` (with an `Arrangement` and an `Alignment.Horizontal`)
  and `Spacer` from the installed wheel, each pixel-equal to the same composables drawn from Kotlin.

### S5.3 `DefaultIcons`, `Icon` and colour schemes: `partial`

`DefaultIcons` is `implemented` against the fake host: `pythonx.compose.material.icons`
(`androidx.compose.material.icons`) serves `Icons`; `Icons.Default` resolves to `Icons.Filled`
and `Icons.Default.Add` is a top-level extension-property getter on `Icons.Filled` (a `GETTER` row,
python-multiplatform #37/#38, read on the proxy); `from pythonx.compose.material3 import DefaultIcons`
is `Icons.Default` by the manifest's `[aliases]` (§2), so `DefaultIcons.Add` is the `ImageVector` and
an unknown icon is an `AttributeError`. An icon is a **property read, written without parentheses**:
the notebook's `DefaultIcons.Add()` would call an `ImageVector`, which is not callable; INTENT §5.7
says the intent is `DefaultIcons.Add`. The rows are shaped after python-multiplatform `31c092f0`
(`_PROPERTIES`, `_read_property`) and the ecosystem report for #37; no walked
`material-icons-core` row exists here, and `Icon(DefaultIcons.Add, ...)` is drawn only in
python-multiplatform's render test and its notebook E2E (cells 28 to 30). Tests: `tests/test_chain.py::DefaultIconsAlias`; stubs: the
`material3` stub assigns `DefaultIcons = Icons.Default` (typed `Icons.Filled`; `Add` is an `ImageVector`, python-multiplatform #68, whose package
`androidx.compose.ui.graphics.vector` is the manifest row `pythonx.compose.ui.graphics.vector`), checked by
`tests/test_typing.py::test_default_icons_imports_from_material3` and `test_a_default_icon_is_an_image_vector`
(`DefaultIcons.Add` is an `ImageVector`, `DefaultIcons.NotAnIcon` an error). `Icon` itself is a Material 3 composable, served by the §3 rule.
Still `planned`: the two colour-scheme factories take 36 `Color` parameters against
the binding's omission cap (python-multiplatform `a6742a1c`). The hand-written `icon.py` /
`color_scheme.py` that recorded this were dead code and are deleted (#31).

### S5.5 `TextField(state=...)` and `TextFieldState`: `partial`

INTENT §5.8. `TextField` uses Compose 1.11's state-based overload, so Compose owns the text buffer
and the IME composing region and no Python callback runs per keystroke. There is no per-widget
wrapper: `pythonx.compose.material3.TextField` is androidx's, re-exported by §3's rule, and its
keywords are `snake_case`. The state comes from `pythonx.compose.foundation.text.input`
(`androidx.compose.foundation.text.input`, a manifest row; a package file with the one-line
re-export, plus a bare `foundation/text/__init__.py` so the wheel finds it):

```python
field = remember_text_field_state("")            # in composition; TextFieldState("hi") outside it
TextField(state=field, modifier=Modifier.padding(8), label=lambda scope: Text("Message"))
field.text                                       # the committed text, a str, read on demand
field.set_text_and_place_cursor_at_end("x")      # extension members, snake_case methods
field.clear_text()
```

`TextField(text_state=...)` and `TextField(..., padding=8)` are a `TypeError` (the binder reports no such
parameter) and a type error in the stubs; the notebook's spelling is `state=` and `modifier=Modifier.padding(8)`
(INTENT §5.8). The `value` / `on_value_change` overloads still exist and are reached by those keywords.
A `TextRange` parameter is the binder's, and `TextRange(2)` is shadowed by a companion module
(python-multiplatform #78); `TextRange__Int(2)` is the spelling meanwhile.

| Behaviour | Test |
|---|---|
| `TextFieldState("hi").text == "hi"`, a `str`; the initial text is optional; Kotlin's `initialText=` works | `tests/test_text_field.py::TheTextFieldState` |
| `set_text_and_place_cursor_at_end` and `clear_text` write | `…::test_set_text_and_place_cursor_at_end_writes_it`, `test_clear_text_empties_it` |
| `remember_text_field_state` is a composable: it needs a composer | `…::test_remember_text_field_state_is_the_composable_that_makes_one`, `…_needs_a_composition` |
| `state=` selects the state overload; keywords are snake_case; `modifier=` reaches it; `value=` selects the `String` overload | `tests/test_text_field.py::TheStateOverload` |
| `text_state=` and `padding=` are a `TypeError` | `…::test_text_state_is_not_a_parameter`, `test_padding_is_not_a_parameter` |
| The stubs type `TextFieldState`, `.text` as `str`, and `TextField(state=...)`; `text_state=` fails | `tests/test_typing.py::test_a_text_field_state_types_the_state_overload`, `test_a_text_field_without_a_kotlin_counterpart_fails` |

Status `partial`: this is wired and tested against the fake host, whose rows are shaped after the stubs of
python-multiplatform `26485a02` (#73), not a walked jar (`tests/fake_host.py` says which fields). The
proof that matters, typing a composing input-method sequence with no Python callback per keystroke
and the field's text asserted afterwards, is python-multiplatform's E2E test (#26), judged over up to
four frames. It passes there (`NotebookTextFieldTest`; python-multiplatform `ksp-fixtures/notebook-e2e` (#26, develop `844cf291`; 20 of 20 passed against this package's `develop` wheel on 2026-10-04, not run here, and no CI workflow runs it yet)): a Hangul sequence
keeps its composing range in Compose, no Python function starts while it types, and the notebook
reads the committed text. Not exercised there: the AWT layer that decodes an `InputMethodEvent`,
which needs a window. Not modelled here: a function-typed slot (`label`, `on_value_change`), which needs
the binder's `NewFunction` rows.

## 6. Modifiers: extension functions as methods

### S6.1 `Modifier` extensions are methods on the receiver proxy: `implemented`

`Modifier.padding(16).size(24)` chains; each link returns a new receiver; an unbound name raises
`AttributeError` naming where it looked; the class-object spelling without a registered empty
factory raises `TypeError` naming `register_empty`; `pythonx.compose.ui.Modifier` is the binder's
proxy class itself.

Evidence: `tests/test_chain.py::TheChain` (8 tests) and
`tests/test_modifier_module.py::TheModifierSeam` (5 tests), against python-multiplatform `ba4c6f49`.
A snake_case method is served by the binder (python-multiplatform #131) and leaves its class Kotlin-named in `dir()`.

### S6.2 The empty-`Modifier` seam: `partial`

`pythonx/compose/ui/modifier.py` provides `install(empty_factory)` to register which Kotlin function
returns an empty `Modifier`, and resolves `Modifier` lazily. **No such function exists in Compose**:
the default `androidx.compose.ui.emptyModifier` is a placeholder, so the class-object spelling
(`Modifier.padding(...)`) does not work against real Compose until an application supplies a
one-line Kotlin factory. The instance spelling (`m.padding(16)` on a `Modifier` Kotlin returned)
does not need it. `tests/test_modifier_module.py::TheShellIsGone` (3 tests, passing) checks the old
hand-written shell is gone.

### S6.3 Overload dispatch: `implemented`

Among Kotlin overloads of one name, a call is dispatched by keyword name, argument count, then
declared type; a non-match names the candidates; an explicit overload spelling (`padding__Dp`)
bypasses dispatch; the module function takes snake_case keywords. Evidence:
`tests/test_chain.py::OverloadDispatch` (7 tests). Status: `implemented`.

### S6.4 Value classes: `implemented`

A raw number is accepted for a `Dp` parameter; a `Dp` value is accepted too; a plain `Float`
parameter is not treated as a value class; a packed value class (`TextUnit`) refuses a raw number and
says why; the allow-list can be extended at run time. The allow-list itself is the manifest's
(S2, implemented) and reaches the binder when a `pythonx.compose` module first resolves a name.
Runtime evidence: `tests/test_chain.py::ValueClasses` (6 tests).

### S6.5 Lazy resolution and handle lifetime: `implemented`

A mapped module is a file on disk and imports without a binder; one with no file is not importable;
a name is adapted once and then lives in the module dict; `dir()` reports the Pythonic names only;
without the binding layer a name read says the host never installed it; dropping a proxy releases
its Kotlin handle. Evidence: `tests/test_chain.py::Laziness` (5 tests), `::Handles` (1 test).

## 7. Layout constants, `Alignment` and `Arrangement`: `implemented`

The bound constant names are documented in `pythonx/compose/ui/alignment.py` (15 `Alignment`
names) and `pythonx/compose/layout/arrangement.py` (8 `Arrangement` names), checked by
`tests/test_alignment_modules.py` (6 tests, passing), whose examples now import the `pythonx`
spelling. The modules contain no code; the constants come from the bindings.

A constant is **read, not called**: `Arrangement.Start`, `Alignment.Center`. The binder reads a
bound static getter on attribute access (`PythonMultiplatform` `46be0212`), so `Alignment.Center()`
raises `TypeError`; the notebook writes the same attribute form.

`pythonx.compose.ui.Alignment` and `pythonx.compose.layout.Arrangement` resolve: an upper-case name
the Kotlin module does not list is tried as a Kotlin object sub-package and served as a
`KotlinObject` namespace by the §3 rule. Constants keep their Kotlin spelling and are read again on
every access; a function inside the object is snake_case (`Arrangement.spaced_by`). Evidence:
`tests/test_chain.py::ObjectNamespaces` (6 tests); without the sub-package step 6 fail. The binder
now lists these objects itself (python-multiplatform #35), and either way reaches them.

A Kotlin object whose name is also a function in its package is **callable**: `Color` is the object
holding `Color.Red` and the function `Color(0xFFFFFFFF)`. The binder makes such a module callable
(python-multiplatform #78), and the namespace serves the same call, so both `Color(0xFFFFFFFF)` and
`Color.Red` work; an object that is no function (`Alignment`) stays uncallable. Evidence:
`tests/test_chain.py::CallableKotlinObjects` (3 tests) and, from the installed wheel rather than the
source tree, `tests/test_wheel.py::TheWheel::test_color_is_callable_from_the_installed_wheel` (#88).

### S7.1 Grouped constants, `Alignment.Horizontal.End`: `implemented`

INTENT §5.3: the notebook groups constants by type, `Alignment.Horizontal.End`, and Kotlin writes
them flat, `Alignment.End` (which *is* an `Alignment.Horizontal`). Both spellings are served, by one
rule that names no declaration:

- Inside the `KotlinObject` for a Kotlin object `P`, an upper-case name `G` that is **not** a member
  of `P` but is the simple name of a type nested in `P` -- some constant of `P` is declared as
  exactly `P.G` -- is a **group**: a namespace whose members are exactly the constants of `P` whose
  declared type is `P.G`. `Alignment.Horizontal` holds `CenterHorizontally`, `End`, `Start`;
  `Alignment.Vertical` holds `Bottom`, `CenterVertically`, `Top`; `Arrangement.HorizontalOrVertical`
  holds `Center`, `SpaceAround`, `SpaceBetween`, `SpaceEvenly`.
- A constant's declared type is read with `python_multiplatform.describe(module, name)`
  (python-multiplatform #36), which answers from the binder's table and never runs the getter. A
  constant's value is never read to classify it. The classification is metadata and is computed
  once per object; values are not cached.
- Reading a group member reads that constant then and there, exactly as the flat spelling does:
  `Alignment.Horizontal.End` and `Alignment.End` are the same read of the same Kotlin getter.
- **A group holds a constant only under its exact declared type.** A constant declared as a
  supertype is in no narrower group: `Alignment.Center` (declared `Alignment`) is in none, and
  `Arrangement.SpaceBetween` (declared `Arrangement.HorizontalOrVertical`) is in
  `Arrangement.HorizontalOrVertical` only, not in `Arrangement.Horizontal`, although Kotlin accepts
  it wherever an `Arrangement.Horizontal` is expected. The notebook groups by declared type, and the
  declared type is what the binder describes; subtyping is not modelled.
- **Kotlin members win.** If `P` has a member named `G` (a constant, a function, a nested object
  the binder lists), that member is what `P.G` reads, and there is no group of that name.
- **In the stubs** (S1.2) the group and the Kotlin type are one class: when the object's stub nests
  a type of the group's name (`class Horizontal` in `Alignment`'s, python-multiplatform #53), the
  group's constants are added to that class, so `Alignment.Horizontal` is the type a parameter
  annotated `Alignment.Horizontal` takes and the namespace `Alignment.Horizontal.End` reads. The
  trade-off: a nested type's members are its grouped constants only (by the exact-declared-type rule
  above), so `Arrangement.Horizontal` lacks the constants declared as `HorizontalOrVertical`; and
  because the first upstream format gave `HorizontalOrVertical` one base, the stubs typed what names it as `Any`;
  with every base listed (python-multiplatform #71) it is typed, and `SpaceBetween` is an `Arrangement.HorizontalOrVertical`.
- `dir()` of an object lists its group names next to its members; `dir()` of a group lists its
  constants. A name a group does not hold raises `AttributeError` naming the group's Kotlin type
  (`androidx.compose.ui.Alignment.Horizontal`), so `Alignment.Horizontal.Top` fails: `Top` is an
  `Alignment.Vertical`.
- On a binder without `describe(module, name)` there are no groups; the flat spelling is unchanged.
- **Stubs.** `scripts/gen_stubs.py` emits each group as a class nested in the object's stub class,
  holding the same `ClassVar` constants, grouped by the declared type the upstream stub's docstring
  carries (`"""Kotlin: androidx.compose.ui.Alignment.End(): androidx.compose.ui.Alignment.Horizontal"""`),
  so a type checker accepts `Alignment.Horizontal.End` and rejects `Alignment.Horizontal.Top`. A
  reference to the Kotlin type `Alignment.Horizontal` in a signature stays `typing.Any`: the group
  class is a namespace, not the type of the constants.

Evidence: `tests/test_chain.py::GroupedObjectConstants` (12 tests, runtime, against the fake host;
with the group lookup disabled 11 fail, and the one that stays green checks the binder without
`describe(module, name)`), `tests/test_stubs.py::TheConstantGroups` (5 tests, generator),
`::TheCommittedStubs::test_the_committed_alignment_and_arrangement_carry_their_groups`,
`::TheStubMatchesTheRuntime::test_a_group_in_the_stub_holds_what_the_runtime_group_holds`, and
`tests/test_typing.py::TheStubsTypeCheck::test_a_grouped_constant_type_checks` (mypy). In the real
`kotlin-stubs` artefact only `Alignment` and `Arrangement` have such groups. Nothing in the walked
Compose surface is an extension receiver named `Alignment.Horizontal` or `Arrangement.Horizontal`, so
the binder lists no member that would win over these groups.

## 8. The notebook surface not yet covered: `planned`

`UI.ipynb` imports or uses these, and nothing in this repository provides them:

| Name | Notebook use | Note |
|---|---|---|
| `remember_saveable` | imported from `pythonx.compose.runtime`; state read/written with `getValue()` / `setValue()` | INTENT §5.1: `state(initial)` read and written through `.value` (S5.4, `partial`, #11; scalars round-trip since python-multiplatform #69); keeping a value across recreation is not provided |
| `DefaultCoroutineScope`, `MainCoroutineScope` | imported from `pythonx.compose.runtime` | INTENT §4.1, open |
| `DefaultIcons` | `DefaultIcons.Add()` | INTENT §5.7, `implemented` as `DefaultIcons.Add`. The notebook's `Add()` is the spelling of its time; the current spelling is `Add`, a property read without parentheses, as for every constant (decided with the ecosystem lead; S5.3, `tests/test_chain.py::DefaultIconsAlias`, fake host) |
| `modifier` | lower-case instance from `pythonx.compose.ui` | INTENT §5.4: not provided; written `Modifier` |
| `color=0xFFFF0000` | ARGB integer for a colour | INTENT §5.5: not accepted; written `Color(0xFFFF0000)` |
| `Spacer(start=..., top=...)` | spacing parameters | INTENT §5.6: not supported; written `Spacer(modifier=Modifier.padding(...))` |
| `Column`, `Row`, `Spacer` | imported from `pythonx.compose.material3` | INTENT §5.2: served from both, by the manifest's `[aliases]` (`tests/test_chain.py::ManifestAliases`); rendered from the installed wheel in python-multiplatform's notebook E2E (#9, S5.2) |
| `TextField(text_state=..., padding=8)` | state object and spacing parameter | INTENT §5.8: written `TextField(state=..., modifier=Modifier.padding(8))`; S5.5, `partial`: IME evidence only in python-multiplatform's notebook E2E (#10) |
| `Card`, `Button`, `Text`, `TextField` | as above | S5.2 |
| `main.App`, `App.update(...)` | live screen replacement from a cell | INTENT §5.1: `@app` declares the root, a redeclaration replaces it, no update function (S5.4, `partial`: real-Compose evidence only in python-multiplatform's notebook E2E, #11) |

## 9. Repository hygiene (not behaviour)

These tests pass and assert that retired 2024 mechanisms are gone. They are not features:

- `tests/test_legacy_modules.py` (4 tests): no chaquopy / JPype tokens or dead relative imports in
  `layout/__init__.py`, `ui/unit/__init__.py`,
  `material3/__init__.py`; each retired module carries a real docstring.
- `tests/test_material3_module.py::TheDeadFilesAreGone` (2 tests): `material3/` holds only its
  `__init__.py`, and `wrapper/` is gone (#31).
- `tests/test_ui_init_module.py::TheChaquopyUiInitMechanismIsGone` (1 test).

---

## Outside intent: needs a decision

Found in the repository; not covered by `docs/INTENT.md`, or in conflict with it.

1. *(Resolved, issue #7.)* Tests and docstrings that assumed a synthesised `pythonx` with
   `__path__ = []` now assert and describe the real package. `ui/modifier.py` still loads by path
   and is rewritten with the re-export (issue #8).
2. *(Resolved, issue #7.)* `tests/adapter.py` no longer asks the binder to rename: it installs
   `python_multiplatform` and `python_multiplatform.binding` from the binder's sources and imports
   `pythonx` from disk. `test_chain.py` and `test_modifier_module.py` still use the old call and
   are rewritten with issue #8.
3. *(Resolved, #60.)* `pythonx/compose/lite/` (the retired 2024 JPype prototype, with 97 tracked
   binaries) is deleted; the tag `archive/pre-restructure` keeps it.
4. **Two spellings for one module.** The manifest maps both `pythonx.compose.layout` and
   `pythonx.compose.foundation.layout` (plus `pythonx.compose.foundation` and `pythonx.compose`)
   "while the spelling settles".
5. *(Resolved, #31.)* `material3/icon.py` and `color_scheme.py`, dead reflection code, are deleted.
6. *(Resolved, INTENT §5.3, issue #9.)* Grouped alignment constants: both spellings are served (§7, S7.1).
7. *(Resolved, #60.)* The submodule `pythonx/compose/native` → `thisisthepy/swing-graalvm-demo`
   (pinned at `090f0190`) is removed; INTENT does not mention it. (The 29 empty `material3/*.py`
   files are deleted, #31.)
8. *(Resolved, #60, INTENT §4.2.)* The `test/` directory, a 2023–2024 Kotlin Multiplatform sample
   (`pycomposeui`, chaquopy era), is deleted; the tag `archive/pre-restructure` keeps it.
