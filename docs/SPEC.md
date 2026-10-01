# Specification

What `pythonx-compose` does — the behavioural contract. Every item stays inside `docs/INTENT.md`;
anything found in the repository that INTENT does not cover is listed at the end under
**Outside intent — needs a decision** rather than written into the contract.

Each item carries a status:

| Status | Meaning |
|---|---|
| `implemented` | Behaviour exists in this repository **and** a test in `tests/` that was read for this document exercises it and passes. |
| `partial` | Some of it exists, or it exists but its tests do not currently pass, or its only evidence is outside this repository. |
| `planned` | Required by INTENT; nothing in this repository delivers it yet. |

A behaviour change starts here, then becomes a failing test, then code (`AGENTS.md` §5).

## 0. Test baseline (2026-10-02)

Run from a worktree with `python3 -m pytest tests -q` (pytest 8, CPython 3.13):

| Environment | Result |
|---|---|
| No `PythonMultiplatform` checkout found | **39 passed, 37 skipped**, 42 subtests passed |
| `PYTHONMULTIPLATFORM_HOME` → the `PythonMultiplatform` checkout | **39 passed, 37 failed**, 42 subtests passed |

The 37 are every test that installs the binder's adaptation layer through `tests/adapter.py`
(`test_chain.py`: 28, `test_modifier_module.py::TheModifierSeam`: 5,
`test_runtime_module.py::TheModuleIsUnreachableByOrdinaryImport`: 2,
`test_ui_init_module.py::TheUiInitModuleIsUnreachableAndDead`: 2). They
fail with `AttributeError: module 'pythonx' has no attribute 'register_package'`: the binder no
longer renames namespaces (INTENT §2.3), and the runtime side that replaces it in this package is
not wired yet. That failure is expected and is why the items below that depend on those tests are
`partial`, not `implemented`.

Of the 39 that pass, most assert **absence** (a retired token, a deleted file, a docstring that
exists). Those are listed in §9 and are not counted as features.

---

## 1. Distribution

### S1.1 Installed as `pythonx-compose`, importing `pythonx.compose` — `partial`

`pyproject.toml` declares `name = "pythonx-compose"`, version `0.0.1`, setuptools build, and
`packages.find include = ["pythonx.compose*"]`.

- Configured: `package-data` carries `*.pyi`, `py.typed` and `pythonx-map.toml` for every package
  (`tests/test_pythonx_map.py::TestManifestShipsWithThePackage::test_the_wheel_is_configured_to_carry_it`).
- Not yet true: no `.pyi` and no `py.typed` exist in the tree, and `pythonx-map.toml` sits at the
  repository root — outside every package directory — so the `package-data` pattern cannot pick it
  up. No test builds a wheel and looks inside it.

### S1.2 Type stubs ship in the wheel — `planned`

Stubs carry the Pythonic names and signatures the runtime resolves, generated from the same
manifest (S2) so the name an editor completes and the name the interpreter resolves cannot drift.
The generator lives in `python-multiplatform`'s Gradle plugin; nothing in this repository produces
or contains a stub yet.

## 2. The mapping manifest (`pythonx-map.toml`) — `implemented`

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

Caveat: `test_the_specification_resolves` reads `UI.ipynb` from the checkout it runs in. The
notebook is git-ignored, so in a worktree or CI checkout it is absent, the expected set is empty,
and **the test passes without checking anything.** It is only meaningful in the maintainer's main
checkout.

## 3. `pythonx` is a real package — `planned`

Required by INTENT §2.2: `import pythonx.compose.material3` (and every other mapped module) loads
**this repository's files on disk**, and those files import the binder-exposed
`androidx.compose.*` modules and present them Pythonically.

Today the opposite structure is in the tree. The module docstrings in
`pythonx/compose/runtime/__init__.py`, `pythonx/compose/ui/__init__.py` and
`pythonx/compose/ui/modifier.py` describe a synthesised `pythonx` with `__path__ = []` that makes
the on-disk files unreachable, and two test classes assert that unreachability
(see "Outside intent" §1). No on-disk module currently re-exports anything from `androidx.compose.*`.

## 4. Naming

### S4.1 Kotlin parameters, `snake_case` — `partial`

`onClick` → `on_click`, `fillMaxWidth` → `fill_max_width`, `zIndex` → `z_index`,
`toURLString` → `to_url_string`; type names (`Modifier`) unchanged; a name the reverse rule cannot
invert still resolves.

Evidence: `tests/test_chain.py::Names` (4 tests). These exercise the conversion in the binder's
adaptation layer through `tests/adapter.py` and are currently skipped or failing (§0). No code in
this repository performs the conversion.

### S4.2 The notebook's spellings are examples, not the contract — `implemented` as a rule

Where `UI.ipynb` writes `onclick`, the surface is `on_click`
(`tests/test_chain.py::Names::test_on_click_not_onclick` records the decision; it is subject to the
same failure as S4.1).

## 5. Composables

### S5.1 `@Composable` decorator — `implemented`

`pythonx.compose.runtime.Composable` is an identity decorator: it returns the exact function it was
given, which still runs and keeps its name and docstring. Composer threading is not the caller's
job.

Tests: `tests/test_runtime_module.py::TheRuntimeSeam` (4 tests) and `::TheChaquopyMechanismIsGone`
(3 tests). The module is loaded **by file path** in these tests, not by `import`, because of §3.

### S5.2 Material 3 composables reach Python without per-widget wrappers — `partial`

`Text`, `Button`, `Card`, `ListItem`, `Badge`, `BadgedBox`, `MaterialTheme`, `IconButton` and its
toggle family, `TextField`, `Checkbox` and `Switch` are meant to be reached through the generated
`androidx.compose.material3` bindings, with no hand-written per-widget module in this package.

- In this repository: only the absence of the old wrapper files is tested
  (`tests/test_material3_module.py`, 8 tests in `TheTextWrapperIsGone`,
  `TheRenderProvenWrappersAreGone`, `TheIconButtonModuleIsEntirelyGone`, `TheTextFieldWrapperIsGone`).
- The evidence that the widgets actually render and deliver callbacks is in `python-multiplatform`
  (commits `a6742a1c`, `3fde8bd6`, `cac8243f`, cited in `pythonx/compose/material3/__init__.py`)
  and was not re-run for this document.
- Nothing in this repository yet re-exports them under `pythonx.compose.material3` (§3).

### S5.3 `Icon` and colour schemes — `partial`

`pythonx/compose/material3/icon.py` and `color_scheme.py` import without raising
(`tests/test_material3_module.py::TheTwoUnreachableWrappersLoadWithoutCrashing`) but are **not
callable**: `Icon` needs an `ImageBitmap` / `ImageVector` / `Painter` nothing bound can produce, and
the two colour-scheme factories take 36 `Color` parameters. The notebook uses `Icon` and
`DefaultIcons` (§8).

## 6. Modifiers — extension functions as methods

### S6.1 `Modifier` extensions are methods on the receiver proxy — `partial`

`Modifier.padding(16).size(24)` chains; each link returns a new receiver; a method is attached to
the proxy type once; an unbound name raises `AttributeError` naming where it looked; the
class-object spelling without a registered empty factory raises `TypeError` naming
`register_empty`.

Evidence: `tests/test_chain.py::TheChain` (6 tests) and
`tests/test_modifier_module.py::TheModifierSeam` (5 tests) — currently skipped or failing (§0).

### S6.2 The empty-`Modifier` seam — `partial`

`pythonx/compose/ui/modifier.py` provides `install(empty_factory)` to register which Kotlin function
returns an empty `Modifier`, and resolves `Modifier` lazily. **No such function exists in Compose**:
the default `androidx.compose.ui.emptyModifier` is a placeholder, so the class-object spelling
(`Modifier.padding(...)`) does not work against real Compose until an application supplies a
one-line Kotlin factory. The instance spelling (`m.padding(16)` on a `Modifier` Kotlin returned)
does not need it. `tests/test_modifier_module.py::TheShellIsGone` (3 tests, passing) checks the old
hand-written shell is gone.

### S6.3 Overload dispatch — `partial`

Among Kotlin overloads of one name, a call is dispatched by keyword name, argument count, then
declared type; a non-match names the candidates; an explicit overload spelling (`padding__Dp`)
bypasses dispatch. Evidence: `tests/test_chain.py::OverloadDispatch` (6 tests), skipped/failing.

### S6.4 Value classes — `partial`

A raw number is accepted for a `Dp` parameter; a `Dp` value is accepted too; a plain `Float`
parameter is not treated as a value class; a packed value class (`TextUnit`) refuses a raw number and
says why; the allow-list can be extended at run time. The allow-list itself is the manifest's
(S2, implemented). Runtime evidence: `tests/test_chain.py::ValueClasses` (5 tests), skipped/failing.

### S6.5 Lazy resolution and handle lifetime — `partial`

A mapped package with bindings is importable, one without is not; a name is adapted once and then
lives in the module dict; `dir()` reports what is bound; dropping a proxy releases its Kotlin
handle. Evidence: `tests/test_chain.py::Laziness` (4 tests), `::Handles` (1 test), skipped/failing.

## 7. Layout constants — `Alignment` and `Arrangement` — `partial`

The bound constant names are documented in `pythonx/compose/ui/alignment.py` (15 `Alignment`
names) and `pythonx/compose/layout/arrangement.py` (8 `Arrangement` names), checked by
`tests/test_alignment_modules.py` (5 tests, passing). The modules contain no code; the constants
come from the bindings.

How a constant is spelled is **not settled**: `alignment.py` and `arrangement.py` say they are
called (`Alignment.Center()`), and the test enforces that text; `pythonx/compose/layout/__init__.py`
says they are read without parentheses (`Arrangement.Start`). The notebook writes
`Alignment.Horizontal.End` (no call). See "Outside intent" §6.

## 8. The notebook surface not yet covered — `planned`

`UI.ipynb` imports or uses these, and nothing in this repository provides them:

| Name | Notebook use | Note |
|---|---|---|
| `remember_saveable` | imported from `pythonx.compose.runtime`; state read/written with `getValue()` / `setValue()` | |
| `DefaultCoroutineScope`, `MainCoroutineScope` | imported from `pythonx.compose.runtime` | |
| `DefaultIcons` | `DefaultIcons.Add()` | needs `Icon` (S5.3) |
| `modifier` | lower-case instance from `pythonx.compose.ui` | INTENT §4 open question 3 |
| `Column`, `Row`, `Spacer` | imported from `pythonx.compose.material3` | Kotlin has them in `foundation.layout`; INTENT §4 question 2 |
| `Card`, `Button`, `Text`, `TextField` | as above | S5.2 |
| `main.App`, `App.update(...)` | live screen replacement from a cell | INTENT §4 question 1 |

## 9. Repository hygiene (not behaviour)

These tests pass and assert that retired 2024 mechanisms are gone. They are not features:

- `tests/test_legacy_modules.py` (7 tests): no chaquopy / JPype tokens or dead relative imports in
  `layout/__init__.py`, `lite/*.py`, `test/main.py`, `ui/unit/__init__.py`, `wrapper/__init__.py`,
  `material3/__init__.py`; each retired module carries a real docstring.
- `tests/test_ui_init_module.py::TheChaquopyUiInitMechanismIsGone` (1 test).

---

## Outside intent — needs a decision

Found in the repository; not covered by `docs/INTENT.md`, or in conflict with it.

1. **Tests and docstrings encode the structure INTENT §2.2 rules out.**
   `tests/test_runtime_module.py::TheModuleIsUnreachableByOrdinaryImport` (2 tests) and
   `tests/test_ui_init_module.py::TheUiInitModuleIsUnreachableAndDead` (2 tests) assert that the
   on-disk `pythonx/compose/...` files *cannot* be imported by their dotted names. The docstrings of
   `runtime/__init__.py`, `ui/__init__.py`, `ui/modifier.py` and `ui/unit/__init__.py` explain the
   package in the same terms. These need rewriting once §3 is designed, not preserving.
2. **The test harness asks the binder to rename.** `tests/adapter.py::install` calls
   `register_package(python_name, kotlin_package)` on the binder's layer for each manifest row —
   the binder-side `androidx` → `pythonx` mapping INTENT §2.3 forbids. That method is gone upstream,
   which is the cause of the 37 failures (§0). The tests in `test_chain.py` and
   `test_modifier_module.py` need a harness that goes through this package's own code instead.
3. **Prebuilt binaries inside the package directory.** `pythonx/compose/lite/release/` tracks 97
   files, including a Windows `.exe`, `.dll` and Compose desktop jars from the 2024 JPype
   prototype, alongside a Gradle project in `pythonx/compose/lite/`.
4. **Two spellings for one module.** The manifest maps both `pythonx.compose.layout` and
   `pythonx.compose.foundation.layout` (plus `pythonx.compose.foundation` and `pythonx.compose`)
   "while the spelling settles".
5. **A removed mechanism kept as a record.** `material3/icon.py` and `color_scheme.py` still import
   `androidx.compose.material3.IconKt` and scan for mangled JVM names (`"Icon-"`), the reflection
   approach INTENT §3 excludes.
6. **Constants called as functions** (`Alignment.Center()`), a limitation of the current bindings,
   is documented as the surface; the notebook reads them as attributes (§7).
7. **28 empty `material3/*.py` files** (`checkbox.py`, `switch.py`, `scaffold.py`, ...), and the
   submodule `pythonx/compose/native` → `thisisthepy/swing-graalvm-demo`, which INTENT does not
   mention.
8. **The `test/` directory** — a 2023–2024 Kotlin Multiplatform sample (`pycomposeui`, chaquopy
   era). Kept as-is pending the maintainer's decision (INTENT §4).
