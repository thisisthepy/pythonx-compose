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

## 0. Test baseline (2026-10-03, after issue #9's grouped constants)

Run from a worktree with `python -m pytest tests -q -rs` (pytest 8, mypy 2.4, CPython 3.13), where
`UI.ipynb` is absent and its one test skips:

| Environment | Result |
|---|---|
| No `PythonMultiplatform` checkout found | **91 passed, 73 skipped**, 122 subtests passed |
| python-multiplatform `develop` at `d6d39787` or later (has `add_member_resolver` and `describe(module, name)`) | **163 passed, 1 skipped**, 149 subtests passed |
| an older checkout, without `describe(module, name)` (python-multiplatform #36) | the same, with 13 more skipped |
| an older one still, without `add_member_resolver` | with 5 more skipped again |

Without a checkout, the 72 tests that install the binder's layers through `tests/adapter.py` skip.
Against a binder without `describe(module, name)`, the 13 that check grouped constants (§7, S7.1)
skip. Against a binder older than `ba4c6f49`, the 5 that call a snake_case method on a proxy the
binder returned skip as well, because that needs its member resolver (python-multiplatform #17). The 1 skip in both
rows is `UI.ipynb`'s (§2). `tests/test_typing.py` skips where mypy is not installed. A skip is not a
pass.

Of the 91 that pass without a checkout, 37 check the type stubs and the wheel (S1.2); most of the
rest assert **absence** (a retired token, a deleted file, a docstring that exists). Those are listed
in §9 and are not counted as features.

---

## 1. Distribution

### S1.1 Installed as `pythonx-compose`, importing `pythonx.compose` — `partial`

`pyproject.toml` declares `name = "pythonx-compose"`, version `0.0.1`, setuptools build,
`requires-python >= 3.11` (the runtime reads the manifest with `tomllib`), and
`packages.find include = ["pythonx.compose*"]`.

- Shipped and tested: `tests/test_wheel.py` builds the wheel from a copy of the sources and finds
  `pythonx/compose/pythonx-map.toml`, the re-export rule, and an `__init__.py` for every mapped
  module (issue #13). The manifest lives inside the package directory so `package-data` carries it.
- Typed: the wheel carries `py.typed` and the generated `.pyi` stubs (S1.2, issue #12).

### S1.2 Type stubs ship in the wheel — `implemented`

Stubs carry the Pythonic names and signatures the runtime resolves, so the name an editor completes
and the name the interpreter resolves cannot drift.

- **What is generated.** `pythonx/compose/**/__init__.pyi` for every module in `pythonx-map.toml`,
  beside its `__init__.py`, and an empty `pythonx/compose/py.typed`. The stubs are committed;
  regenerating them from the same input produces no diff.
- **From what.** python-multiplatform's CI artefact `kotlin-stubs` (workflow run 37077627980,
  commit `86012ca0`): Kotlin-named stubs for Compose 1.11.1, one `androidx/compose/.../__init__.pyi`
  per Kotlin package. `python3 tools/gen_stubs.py <kotlin-stubs.zip or directory>` converts them;
  the first line of every generated stub records the artefact, run and commit it came from.
- **The rule is the runtime's** (`_reexport.py`), applied by `tools/gen_stubs.py`:
  - a module function or constant is renamed with `python_name` (upper-case names kept, others
    snake_case, an explicit overload keeps its suffix: `padding__Dp`); its parameters are
    snake_case, except the positional-only `receiver` and anonymous `__aN` slots; keyword-only
    markers and the binder's `@overload` sets, in the binder's order, are kept;
  - a stub class keeps its name. Its extension members (`Modifier.fill_max_width`, a
    `ClassVar` of a callable `Protocol`) are renamed with `python_name`, the member resolver's rule,
    but the protocol's parameter names stay Kotlin's, because the runtime does not translate a
    method's keywords yet (§3); every generated stub says so in its header;
  - a Kotlin object served as a sub-package (`Alignment`, `Arrangement`) becomes a class of that
    name in its parent module's stub, its constants `ClassVar`s and its functions snake_case
    static methods. A sub-package directory holding only `__init__.pyi` would be a namespace
    package at run time and would shadow the `KotlinObject` the re-export rule serves. The
    generator reads both upstream layouts: the object as its own `<Object>/__init__.pyi`, or as a
    class inside the parent stub (python-multiplatform #44). An object whose name the parent module
    also uses for a function (`Color`, `TextStyle`, `PaddingValues`, `TextUnit`) is left out,
    because at run time that name reaches the function;
  - a reference to another Kotlin package is rewritten to the `pythonx.compose` module the
    manifest lists first for it (`androidx.compose.foundation.layout` → `pythonx.compose.layout`);
    a reference to a package the manifest does not map, or to a name the target stub does not
    declare, becomes `typing.Any`;
  - a module that maps the same Kotlin package as an earlier one (`pythonx.compose.foundation.layout`)
    re-exports it (`from pythonx.compose.layout import *`), since at run time both names reach the
    same objects; `[aliases]` become re-exports too (`material3` exports `Column`, `Row`, `Spacer`
    from `pythonx.compose.layout`); names a package defines itself (`runtime.Composable`) are
    carried over.
- **How it is verified.** `tests/test_stubs.py` converts two fixtures holding the fake host's
  declarations, in the old and the current upstream format (and the current format with an object
  in its parent stub), and checks the generated signatures against `inspect.signature` at run time.
  `TheCommittedStubs` regenerates from `.tmp/kotlin-stubs.zip` and requires the committed files to
  be identical (it skips where the artefact is absent, which includes CI). `tests/test_typing.py`
  runs mypy over small programs against the committed stubs: correct code passes, a misspelled
  keyword or function fails. `tests/test_wheel.py` finds `py.typed` and the stubs in the built wheel.
  Disabling a step of the generator fails tests: folding objects into their parent 11, rewriting
  references 9, keeping the binder's `# type: ignore` comments 7, renaming class members 5, the
  second-module re-export 2, the aliases 2, the shadowed-object check 1.
- **Still missing.**
  - Many parameter and return types are `Any`: upstream emits `Any` for a class that shares its
    name with a function (`PaddingValues`, `TextStyle`, `Color`) and for packages it does not stub;
    `Dp` is `float`.
  - A method's keywords are Kotlin's in the stub because they are Kotlin's at run time (S4.1).
  - The `pythonx.compose` root module maps `androidx.compose`, which has no stub, so its stub is
    empty.
  - Object constants named like a Python keyword (`FilterQuality.None`) cannot be written as an
    attribute, and are left out.
  - Regenerating needs the artefact downloaded by hand into `.tmp/`; CI does not fetch it.

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

## 3. `pythonx` is a real package — `implemented` (module level)

Required by INTENT §2.2: `import pythonx.compose.material3` (and every other mapped module) loads
**this repository's files on disk**, and those files import the binder-exposed
`androidx.compose.*` modules and present them Pythonically.

Every module in `pythonx-map.toml` is a file on disk whose `__init__.py` hands its name to one rule,
`pythonx/compose/_reexport.py` (issue #8). A name read from it resolves, on first use, against the
Kotlin package the manifest maps it to: upper-case names keep their Kotlin spelling, every other
name is reached by its snake_case spelling only, keywords are matched to the declaration's own
parameter names, `inspect.signature` reports snake_case names, and the manifest's value-class
allowlist is handed to the binder. Names the package defines itself (`runtime.Composable`) win.

Evidence: `tests/test_runtime_module.py::TheModuleIsTheFileOnDisk`,
`tests/test_ui_init_module.py::TheUiInitModuleIsTheFileOnDisk`, and `tests/test_chain.py`
(`Names`, `Laziness`, `OverloadDispatch::test_the_module_function_dispatches_with_snake_case_keywords`,
`ValueClasses::test_the_manifest_allowlist_is_what_lets_a_number_through`), against the binder's
real Python and the fake host. Disabling the name rule fails 15 tests, the keyword mapping 1, the
allowlist priming 12.

Methods on a proxy the binder returned (`m.fill_max_width()`) are attributes of the binder's own
class. The same rule reaches them as the binder's member resolver (`member_name`, registered through
`python_multiplatform.binding.add_member_resolver`, python-multiplatform `ba4c6f49`); the binder
caches the alias in its own registry, so its class keeps Kotlin names in `dir()` (issue #20).
Keyword arguments to such a method are still Kotlin's own (`m.padding(paddingValues=...)`): the
resolver maps names, not keywords.

## 4. Naming

### S4.1 Kotlin parameters, `snake_case` — `partial` (method keywords)

`onClick` → `on_click`, `fillMaxWidth` → `fill_max_width`, `zIndex` → `z_index`,
`toURLString` → `to_url_string`; type names (`Modifier`) unchanged; an explicit overload keeps its
type suffix (`padding__Dp_Dp`); a name the reverse rule cannot invert still resolves, because the
rule is only ever applied forward to the module's real names; the camelCase spelling is not a second
name.

Implemented for module-level names and keywords and for method names on a binder proxy
(`tests/test_chain.py::Names`, 8 tests; `TheChain`). Partial because a method's keyword arguments are
still Kotlin's (§3).

### S4.2 The notebook's spellings are examples, not the contract — `implemented` as a rule

Where `UI.ipynb` writes `onclick`, the surface is `on_click`
(`tests/test_chain.py::Names::test_on_click_not_onclick` records the decision).

## 5. Composables

### S5.1 `@Composable` decorator — `implemented`

`pythonx.compose.runtime.Composable` is an identity decorator: it returns the exact function it was
given, which still runs and keeps its name and docstring. Composer threading is not the caller's
job.

Tests: `tests/test_runtime_module.py::TheRuntimeSeam` (4 tests) and `::TheChaquopyMechanismIsGone`
(3 tests), importing `pythonx.compose.runtime` the ordinary way.

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
- `pythonx.compose.material3` re-exports `androidx.compose.material3` by the §3 rule, but the fake
  host binds no material3 declaration, so no test here exercises one; the render proof per widget
  is issue #9.

### S5.3 `Icon` and colour schemes — `planned`

`Icon` needs an `ImageBitmap` / `ImageVector` / `Painter`, and nothing bound produces one until the
binder walks `material-icons-core` (python-multiplatform #37; then `DefaultIcons` is
`Icons.Default`, INTENT §5.7). The two colour-scheme factories take 36 `Color` parameters against
the binding's omission cap (python-multiplatform `a6742a1c`). The hand-written `icon.py` /
`color_scheme.py` that recorded this were dead code and are deleted (#31).

## 6. Modifiers — extension functions as methods

### S6.1 `Modifier` extensions are methods on the receiver proxy — `implemented`

`Modifier.padding(16).size(24)` chains; each link returns a new receiver; an unbound name raises
`AttributeError` naming where it looked; the class-object spelling without a registered empty
factory raises `TypeError` naming `register_empty`; `pythonx.compose.ui.Modifier` is the binder's
proxy class itself.

Evidence: `tests/test_chain.py::TheChain` (8 tests) and
`tests/test_modifier_module.py::TheModifierSeam` (5 tests), against python-multiplatform `ba4c6f49`.
A snake_case method resolved through the member rule leaves the binder's class Kotlin-named.

### S6.2 The empty-`Modifier` seam — `partial`

`pythonx/compose/ui/modifier.py` provides `install(empty_factory)` to register which Kotlin function
returns an empty `Modifier`, and resolves `Modifier` lazily. **No such function exists in Compose**:
the default `androidx.compose.ui.emptyModifier` is a placeholder, so the class-object spelling
(`Modifier.padding(...)`) does not work against real Compose until an application supplies a
one-line Kotlin factory. The instance spelling (`m.padding(16)` on a `Modifier` Kotlin returned)
does not need it. `tests/test_modifier_module.py::TheShellIsGone` (3 tests, passing) checks the old
hand-written shell is gone.

### S6.3 Overload dispatch — `implemented`

Among Kotlin overloads of one name, a call is dispatched by keyword name, argument count, then
declared type; a non-match names the candidates; an explicit overload spelling (`padding__Dp`)
bypasses dispatch; the module function takes snake_case keywords. Evidence:
`tests/test_chain.py::OverloadDispatch` (7 tests). Status: `implemented`.

### S6.4 Value classes — `implemented`

A raw number is accepted for a `Dp` parameter; a `Dp` value is accepted too; a plain `Float`
parameter is not treated as a value class; a packed value class (`TextUnit`) refuses a raw number and
says why; the allow-list can be extended at run time. The allow-list itself is the manifest's
(S2, implemented) and reaches the binder when a `pythonx.compose` module first resolves a name.
Runtime evidence: `tests/test_chain.py::ValueClasses` (6 tests).

### S6.5 Lazy resolution and handle lifetime — `implemented`

A mapped module is a file on disk and imports without a binder; one with no file is not importable;
a name is adapted once and then lives in the module dict; `dir()` reports the Pythonic names only;
without the binding layer a name read says the host never installed it; dropping a proxy releases
its Kotlin handle. Evidence: `tests/test_chain.py::Laziness` (5 tests), `::Handles` (1 test).

## 7. Layout constants — `Alignment` and `Arrangement` — `implemented`

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

### S7.1 Grouped constants — `Alignment.Horizontal.End` — `implemented`

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
- `dir()` of an object lists its group names next to its members; `dir()` of a group lists its
  constants. A name a group does not hold raises `AttributeError` naming the group's Kotlin type
  (`androidx.compose.ui.Alignment.Horizontal`), so `Alignment.Horizontal.Top` fails: `Top` is an
  `Alignment.Vertical`.
- On a binder without `describe(module, name)` there are no groups; the flat spelling is unchanged.
- **Stubs.** `tools/gen_stubs.py` emits each group as a class nested in the object's stub class,
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

## 8. The notebook surface not yet covered — `planned`

`UI.ipynb` imports or uses these, and nothing in this repository provides them:

| Name | Notebook use | Note |
|---|---|---|
| `remember_saveable` | imported from `pythonx.compose.runtime`; state read/written with `getValue()` / `setValue()` | INTENT §5.1: Pythonic attribute access instead of the accessors |
| `DefaultCoroutineScope`, `MainCoroutineScope` | imported from `pythonx.compose.runtime` | INTENT §4.1, open |
| `DefaultIcons` | `DefaultIcons.Add()` | INTENT §5.7: `Icons.Default` by alias, once python-multiplatform #37 binds `material-icons-core` |
| `modifier` | lower-case instance from `pythonx.compose.ui` | INTENT §5.4: not provided; written `Modifier` |
| `color=0xFFFF0000` | ARGB integer for a colour | INTENT §5.5: not accepted; written `Color(0xFFFF0000)` |
| `Spacer(start=..., top=...)` | spacing parameters | INTENT §5.6: not supported; written `Spacer(modifier=Modifier.padding(...))` |
| `Column`, `Row`, `Spacer` | imported from `pythonx.compose.material3` | INTENT §5.2: served from both, by the manifest's `[aliases]` (`tests/test_chain.py::ManifestAliases`); render proof pending (#9) |
| `Card`, `Button`, `Text`, `TextField` | as above | S5.2 |
| `main.App`, `App.update(...)` | live screen replacement from a cell | INTENT §5.1: a declared root that a redefinition replaces, no update function (issue #11) |

## 9. Repository hygiene (not behaviour)

These tests pass and assert that retired 2024 mechanisms are gone. They are not features:

- `tests/test_legacy_modules.py` (6 tests): no chaquopy / JPype tokens or dead relative imports in
  `layout/__init__.py`, `lite/*.py`, `test/main.py`, `ui/unit/__init__.py`,
  `material3/__init__.py`; each retired module carries a real docstring.
- `tests/test_material3_module.py::TheDeadFilesAreGone` (2 tests): `material3/` holds only its
  `__init__.py`, and `wrapper/` is gone (#31).
- `tests/test_ui_init_module.py::TheChaquopyUiInitMechanismIsGone` (1 test).

---

## Outside intent — needs a decision

Found in the repository; not covered by `docs/INTENT.md`, or in conflict with it.

1. *(Resolved, issue #7.)* Tests and docstrings that assumed a synthesised `pythonx` with
   `__path__ = []` now assert and describe the real package. `ui/modifier.py` still loads by path
   and is rewritten with the re-export (issue #8).
2. *(Resolved, issue #7.)* `tests/adapter.py` no longer asks the binder to rename: it installs
   `python_multiplatform` and `python_multiplatform.binding` from the binder's sources and imports
   `pythonx` from disk. `test_chain.py` and `test_modifier_module.py` still use the old call and
   are rewritten with issue #8.
3. **Prebuilt binaries inside the package directory.** `pythonx/compose/lite/release/` tracks 97
   files, including a Windows `.exe`, `.dll` and Compose desktop jars from the 2024 JPype
   prototype, alongside a Gradle project in `pythonx/compose/lite/`.
4. **Two spellings for one module.** The manifest maps both `pythonx.compose.layout` and
   `pythonx.compose.foundation.layout` (plus `pythonx.compose.foundation` and `pythonx.compose`)
   "while the spelling settles".
5. *(Resolved, #31.)* `material3/icon.py` and `color_scheme.py`, dead reflection code, are deleted.
6. *(Resolved, INTENT §5.3, issue #9.)* Grouped alignment constants: both spellings are served (§7, S7.1).
7. The submodule `pythonx/compose/native` → `thisisthepy/swing-graalvm-demo`, which INTENT does not
   mention. (The 29 empty `material3/*.py` files are deleted, #31.)
8. **The `test/` directory** — a 2023–2024 Kotlin Multiplatform sample (`pycomposeui`, chaquopy
   era). Kept as-is pending the maintainer's decision (INTENT §4.2).
