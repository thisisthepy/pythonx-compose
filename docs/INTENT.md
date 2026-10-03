# Intent

Why `pythonx-compose` exists, what it is for, and what it deliberately is not.
`docs/SPEC.md` may not go beyond this file. When the two disagree, this file wins; when this file
and the user's own words disagree, the user's words win.

## Sources

Everything below is derived from these, in this order of authority:

1. **The user's statements**, quoted verbatim where they are used.
2. **`UI.ipynb`** — the user's notebook and this project's user-facing specification. It is
   untracked and git-ignored; it lives only in the maintainer's main checkout and is never copied,
   moved, or added.
3. The repository's original README (2023–2024): *"pythonx is a python extension for kotlin
   integration"* — *"Python Wrapper for Kotlin Compose Multiplatform."*
4. Recorded decisions in `python-multiplatform` (`docs/ecosystem.md` §5b,
   `docs/kotlin-extensions-in-python.md` §4). These are records of work, not requirements; they are
   used only where they agree with 1–3.

Anything that is an inference rather than a statement is marked:

> Inferred — confirm with the maintainer.

---

## 1. What this project is for

**Writing Compose user interfaces in Python.** A Python programmer imports `pythonx.compose.*`,
writes `@Composable` functions, and gets real Jetpack / Compose Multiplatform UI — the same widgets,
the same parameters, spelled the way Python spells things.

The notebook shows the experience this is for: a running app whose screen is replaced from a
notebook cell (`main.App.update(Practice)`), whose state is read and written from Python
(`main.App.messages.getValue()` / `setValue(...)`), and whose widgets — `Text`, `Button`, `Card`,
`Icon`, `TextField`, `Column`, `Row`, `Spacer` — are called from ordinary Python functions. The
notebook is titled *"Python 앱 개발 특강"* (a lecture on Python app development): the audience is
people who know Python and want to build an app without first learning Kotlin.

## 2. What it is, structurally

These are constraints the user stated, not design options.

### 2.1 A pip package named `pythonx-compose`

> "pythonx-compose는 pip 패키지 pythonx-compose로 배포될 물건이야"

It ships as the distribution **`pythonx-compose`**, installed with `pip`, providing the import
package `pythonx.compose`.

### 2.2 `pythonx` is a real Python package on disk

> "pythonx 에는 실제 패키지가 존재해야 해. pythonx의 코드는 androidx 모듈을 가져와서 pythonic 하게
> 사용 가능하도록 구조를 수정"

`pythonx/compose/...` is real, importable Python source. Its code **imports the `androidx.compose.*`
modules** and **restructures them** so they can be used Pythonically. It is not a namespace that
something else synthesises at run time.

### 2.3 The binder never renames; renaming is this package's job

`python-multiplatform` (the binder) exposes Kotlin declarations to Python **under their Kotlin
names** — `androidx.compose.material3` in Kotlin is `androidx.compose.material3` in Python. The
binder must never turn `androidx` into `pythonx` or rename any other Kotlin namespace. Mapping
`androidx.compose.*` to `pythonx.compose.*` is done **here, in real Python code**.

`pythonx-map.toml` in this repository is the mapping manifest: which `pythonx.compose.*` module
stands for which Kotlin package, and which value classes may be written as raw numbers.

### 2.4 The Python surface is the original Kotlin API, spelled Pythonically

The rule: **expose the original Kotlin parameters, with Pythonic `snake_case` names.**
`onClick` becomes `on_click`; `horizontalAlignment` becomes `horizontal_alignment`; type names stay
as they are (`Modifier`, `Alignment`).

The function signatures written in `UI.ipynb` (`Button(onclick, corner_radius, color, ...)`,
`Spacer(start, top, end, bottom)`, ...) are **naming examples**, not the contract. Where the
notebook's spelling and the Kotlin parameter disagree, the Kotlin parameter, snake-cased, wins.

### 2.5 Kotlin extension functions are methods on the receiver

A Kotlin extension function such as `Modifier.padding` appears in Python as a method on the
receiver's proxy object, so a chain reads the way it does in Kotlin:

```python
Modifier.padding(16).size(24)
```

### 2.6 `@Composable` stays

Screens are written as `@Composable`-decorated Python functions, as the notebook writes them.

### 2.7 Type stubs ship in the package

`.pyi` stubs ship inside the wheel so an editor sees the full Pythonic surface — names, parameters,
types — even though the runtime resolves bindings on demand.

---

## 3. What this project deliberately is not

- **Not the binder.** Embedding CPython, the FFI, upcalls and the artefact walker belong to
  `python-multiplatform`. This package depends on that surface; it does not reimplement it.
- **Not a renamer inside the binder.** Nothing that maps `androidx` to `pythonx` may live in
  `python-multiplatform` (§2.3).
- **Not a reimplementation of Compose.** Widgets are Compose's own; this package changes how they
  are named and reached from Python, not what they do.
- **Not an invented API.** Parameters that do not exist in Kotlin (for example the notebook's
  `corner_radius` on `Button`) are not added just because an example used them.
  > Inferred — confirm with the maintainer. (Follows from §2.4; the user has not ruled on
  > convenience parameters explicitly.)
- **Not runtime reflection.** The chaquopy-era approach — `jclass(...)` lookups and scanning
  mangled JVM names such as `Text-fLXpl1I` — is a removed option. Bindings are produced at build
  time because GraalVM native images and Kotlin/Native have no reflection
  (`python-multiplatform` `docs/ecosystem.md` §5b).
- **Not a hand-written Kotlin wrapper layer.** The Pythonic restructuring happens in Python, over
  the generated `androidx.compose.*` bindings, not in a Kotlin module written per widget
  (`python-multiplatform` `docs/ecosystem.md` §5b).

---

## 4. Open questions the intent does not settle

These are recorded so that `docs/SPEC.md` does not settle them by accident.

1. **Coroutine scopes** the notebook imports, `DefaultCoroutineScope` / `MainCoroutineScope`.
   (The other convenience spellings are decided, §5.4–5.7.)
2. **The `test/` directory** — a 2023–2024 Kotlin Multiplatform sample (`pycomposeui`). Whether it
   is kept, moved, or removed is the maintainer's decision.

## 5. Decided (2026-10-03)

Settled by the maintainer, relayed through the ecosystem lead, and recorded here so the spec follows
them.

1. **A declared app root, no update function.** The notebook's `main.App.update(...)` and
   `getValue()` / `setValue()` calls were the constraints of the implementation at the time, not the
   specification. The maintainer, verbatim:

   > "main.App.update() 말고 좀 더 선언형으로 갈 수 있는 API로 해줘. UI.ipynb에 그렇게 되어 있는건
   > 어쩔 수 없는 구현이었고 내가 원한는건 좀 더 선언형 형식이었어. 업데이트 함수가 명시적으로
   > 존재하면 안되는거잖아."

   What the notebook shows is the intent: redefining the UI in a cell changes the screen, and the
   notebook and the screen see the same state. So the public API has **no explicit refresh call**.
   The root is *declared*; redefining it is what changes the screen. State follows Compose's state
   model: a composable that reads a state object recomposes when it changes, and state is read and
   written through Pythonic attributes rather than Java-style accessors. `main` itself is the
   application's module, not this package; this package provides the mechanism.
2. **`Column`, `Row`, `Spacer` are importable from `pythonx.compose.material3`** as the notebook
   writes, and from their Kotlin home (`pythonx.compose.layout`) as well.
3. **Alignment constants in both spellings:** Kotlin's flat `Alignment.End`, and the notebook's
   grouping by type, `Alignment.Horizontal.End` (in Kotlin `Alignment.End` *is* an
   `Alignment.Horizontal`).
4. **No lower-case `modifier`.** In Kotlin the empty modifier *is* `Modifier` (its companion); the
   lower-case instance was the 2024 implementation's second name, and the archived design already
   concluded to drop it. The notebook's `modifier=modifier` is written `modifier=Modifier`.
5. **Colours are explicit.** A raw integer is not accepted for a `Color` parameter (`Color` packs
   several fields into one value, so a number would decode as something else). The notebook's
   `color=0xFFFF0000` is written `color=Color(0xFFFF0000)`, through Kotlin's own `Color` factory.
6. **No parameters Kotlin does not have.** `Spacer(start=..., top=...)` is not supported; the
   intent is written `Spacer(modifier=Modifier.padding(...))`.
7. **`DefaultIcons` is `Icons.Default`,** served by name once the binder walks
   `material-icons-core` (python-multiplatform #37).
8. **`TextField` takes a `TextFieldState`; no `text_state`, no `padding`.** The notebook's
   `TextField(text_state=..., padding=8)` has no Kotlin counterpart, so under 5.6 it is written
   `TextField(state=..., modifier=Modifier.padding(8))`. Compose 1.11's state-based overload keeps
   the text buffer and the input method's composing region inside Compose, so nothing crosses into
   Python per keystroke; the `value` / `on_value_change` overloads send a `str` back on every key
   and lose the composing range. Python makes the state with `remember_text_field_state("")` (inside
   composition) or `TextFieldState("hi")` (outside, such as a notebook cell), from
   `pythonx.compose.foundation.text.input`, and reads or writes it on demand: `field.text`,
   `field.set_text_and_place_cursor_at_end("x")`, `field.clear_text()`. `TextField` itself is
   androidx's, re-exported by rule, with no per-widget wrapper (§2.4). The input field's state is
   separate from state a screen streams output into.
