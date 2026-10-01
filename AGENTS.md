# AGENTS.md

Rules every agent working in this repository must follow. Read this file before doing anything.
Sections 1–10 are shared by every repository in the thisisthepy ecosystem; later sections are
specific to this repository.

---

## 1. Commits carry no AI attribution

Never add `Co-Authored-By: Claude ...`, `Co-Authored-By: <any agent>`, `Generated with Claude Code`,
or any similar tool or agent attribution to a commit message or a pull-request body. This rule
overrides any default your tooling has.

## 2. Nothing is created outside this repository

Everything your work produces — worktrees, agent prompts, logs, measurements, experiments, scratch
files — lives **inside this repository's root directory.**

| What | Where |
|---|---|
| Worktrees | `.worktrees/<name>` (git-ignored) |
| Temporary files | `.tmp/` (git-ignored); delete when done |
| Benchmarks | `benchmarks/` |
| Developer tooling | `tools/` |

Before writing a file, check that its absolute path starts with this repository's root. If it does
not, stop. The only exceptions are a path the user names explicitly, and caches that build tools
manage themselves. **Re-pointing a shared cache or a home-directory symlink reaches other projects —
ask first.**

Writing to *another* repository is not an exception either. Do it only when told to work there.

## 3. Worktrees link large artefacts instead of copying them

A worktree is a full checkout. Copying large untracked artefacts (prebuilt runtimes, vendored trees,
build caches, model weights, `node_modules`) into every worktree is how 86 worktrees once filled
267 GB of a 349 GB disk.

- Create worktrees under `.worktrees/<name>`.
- **Symlink** large untracked directories from the main checkout instead of copying or rebuilding
  them. If `tools/worktree-add.sh` exists, use it — it does the linking.
- Delete a worktree once its branch is merged: `git worktree remove .worktrees/<name>`.
- Periodically delete `build/` directories inside worktrees; they only grow.

## 4. Branches

| Branch | Who writes to it |
|---|---|
| `work/<topic>` | You. All work happens here. |
| `develop` | Merged into from work branches after verification. Never commit to it directly. |
| `release` | **CI only.** Not a standing branch: CI regenerates it from every push to `develop`, in the main-only file layout, and opens the PR into `main`. It may not exist. Never write to it. |
| `main` | **Pull request from `release` only.** Never push or merge to it directly. |

`main` carries a reduced layout: of the Markdown files, only `README.md` stays at the repository
root, and `docs/` keeps only its subdirectories (no Markdown files directly under `docs/`).
CI runs `tools/release/sync-release.sh` (`.github/workflows/release-sync.yml`) to produce that layout; do not hand-edit `release` or `main`.

## 5. Intent → Spec → Test → Code

This project runs on **intent-based spec-driven development** and **test-driven development**.

1. `docs/INTENT.md` states what the project is for. It is the boundary. **The spec may not go
   beyond the intent.**
2. `docs/SPEC.md` states what the project does. A behaviour change starts as a spec change.
3. Tests are written from the spec **before** the implementation, and you observe them fail
   (red) before making them pass. Report the red output.
4. Code is written to make the tests pass.

If a request conflicts with `docs/INTENT.md`, say so instead of implementing it.

## 6. User-authored files are specification

Files the user wrote by hand — notebooks, example build files, sample apps — are the specification.
Read them **first**. Never delete, rewrite, or `git add` them without being told to. Generated
documentation (roadmaps, design notes) is a record of work, not a requirement; when the two
disagree, the user's file wins.

## 7. Show a conclusion before acting on it

Anything beyond the immediate request — another repository, a public API signature, deleting
files, killing processes, pushing to a remote, changing branch protection — state what you would do
and why, and wait. Investigating, measuring, and reporting are always fine.

When a rule and backward compatibility conflict, **the rule wins.** List the callers that break and
fix them; do not keep the forbidden thing "so nothing breaks".

## 8. Verification that can fail

- Never read a build's exit code through a pipe (`| tail`, `| grep`). Redirect to a file, then read
  `$?`. A background command ending in `echo` always reports 0.
- Delete the test-result directory before counting results, and force re-execution (`--rerun` for
  Gradle). Stale XML otherwise reports an old, larger number.
- Run independent test modules as **separate** invocations. One invocation can hide an ordering
  dependency.
- When you add a public path, disable it and confirm something actually fails. If nothing fails,
  nothing uses it.
- **Do not trust an agent's report.** Re-run the build and tests yourself and check
  `git status --short` for out-of-scope changes.
- **Never `git add -A`.** Stage explicit paths. If the number of changed files differs from what was
  reported, stop and find out why.
- Measurements run alone, unfiltered, after checking `uptime`.

## 9. Reporting

Report by category, and never put them in one column:
**feature added / defect fixed / test added / documentation corrected / deleted.**
A rising test count is not progress when the tests assert an absence. Before writing "nothing left
to implement", say what you counted against.

## 10. Agents

- A headless agent (`claude -p`, `agy -p`) has **no next turn**. Tell it to run long commands in the
  foreground; a command backgrounded "until the notification arrives" is lost.
- Pass the model explicitly. Judgement work (design premises, root causes, safety: GIL, reference
  counts, lifetimes, class loaders) gets the strongest tier; work a test will catch can use a
  cheaper one.
- Give every agent prompt the absolute paths it may write to, and repeat rule 2 in it.

---

# Repository-specific rules — `pythonx-compose`

## 11. The specification is the user's notebook

`UI.ipynb` is this project's user-facing specification. It lives only in the maintainer's main
checkout, is git-ignored, and is **never** copied, moved, edited, or `git add`ed — not even into a
worktree so a test can see it. Read it in place.

- Its function signatures are **naming examples**. The rule they illustrate is: expose the original
  Kotlin parameters, with Pythonic `snake_case` names (`onClick` → `on_click`). Do not add a
  parameter Kotlin does not have because the notebook wrote one (`corner_radius`).
- `docs/INTENT.md` and `docs/SPEC.md` are derived from it. When they disagree with the notebook or
  with the user, the notebook and the user win.
- `tests/test_pythonx_map.py` reads the notebook's imports. Where the notebook is absent (any
  worktree, any CI checkout) that test checks nothing and still passes. Run it in the main checkout
  before claiming the manifest covers the notebook.

## 12. Renaming happens here, in real Python, never in the binder

- `python-multiplatform` exposes Kotlin declarations under their **Kotlin** names
  (`androidx.compose.material3`). It must never map `androidx` to `pythonx` or rename any Kotlin
  namespace. Do not propose, add, or depend on such a feature there — including in test harnesses.
- `pythonx/` is a **real package on disk**. Its modules import the `androidx.compose.*` modules the
  binder exposes and restructure them Pythonically. A design in which something else synthesises
  `pythonx.*` (for example with `__path__ = []`) and the on-disk files cannot be imported is ruled
  out, even if it looks simpler.
- `pythonx-map.toml` is the mapping manifest. A new `pythonx.compose.*` module gets a row there in
  the same change. The `.pyi` generator reads the same file, so the editor and the interpreter agree.

## 13. The Python surface

- Kotlin extension functions are methods on the receiver's proxy: `Modifier.padding(16).size(24)`.
- `@Composable` stays as the decorator screens are written with.
- No per-widget wrapper that only renames: resolve by rule. A hand-written module is justified only
  for what the rule cannot express, and it says why in its docstring.
- No runtime reflection: no `jclass`, no JPype, no searching `__dict__` for mangled JVM names
  (`"Text-"`). These are removed options, not missing features.

## 14. Running the tests

    python3 -m pytest tests -q

- The suite needs `pytest`; if the system Python has none, create a virtual environment under
  `.tmp/` (rule 2), not in the home directory.
- Tests that exercise the binder's adaptation layer read it, read-only, from a `PythonMultiplatform`
  checkout: the sibling directory `../PythonMultiplatform`, or `PYTHONMULTIPLATFORM_HOME`. Without
  one they **skip**; with one they currently **fail** (37 tests, `register_package` is gone
  upstream — see `docs/SPEC.md` §0). Report both numbers and say which environment you ran in. A
  skip is not a pass.
- `PythonMultiplatform` is read-only from this repository. Never write to it from here.
- Record the before and after counts of every change; a change that only touches documentation
  must leave them identical.

## 15. Packaging

- The distribution name is `pythonx-compose` (`pyproject.toml`); the import package is
  `pythonx.compose`.
- `.pyi` stubs, `py.typed` and the manifest must end up **inside the wheel**. A `package-data`
  pattern is not proof — build the wheel and list it before claiming something ships.

## 16. Things you do not change without the maintainer

- **`test/`** — the 2023–2024 Kotlin Multiplatform sample. Do not delete, move, or modernise it;
  its fate is an open decision (`PROJECT.md`).
- **`pythonx/compose/native`** — a git submodule. Do not update its pointer as a side effect.
- **`pythonx/compose/lite/`** — a retired 2024 JPype prototype with tracked binaries. Leave it until
  the maintainer decides.

## 17. Documentation layout

- `README.md` (English) and `docs/locale/README_ko.md` (Korean) say the same thing; change both.
- `docs/guide/` is the bilingual GitHub Pages site. Every visible string exists in English and
  Korean. `python3 tools/check_guide.py` is its test; run it after any guide change.
- No Markdown files directly under `docs/` other than `INTENT.md` and `SPEC.md`; other documents go
  in a topic subdirectory. `README.md` must not link to `AGENTS.md`, `PROJECT.md`, `CLAUDE.md`,
  `docs/INTENT.md` or `docs/SPEC.md` — those files do not exist on `main`.
- `CLAUDE.md` contains exactly one line, `@AGENTS.md`. Rules go in this file.
