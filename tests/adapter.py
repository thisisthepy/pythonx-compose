"""Install the binder's Python layers, read out of a `PythonMultiplatform` checkout.

The binder ships two hand-written Python sources as Kotlin raw-string literals, and `exec`s them at
run time for the reason `PythonxAdapter.kt` gives (on iOS, androidNative and wasm there is no
resource path a `.py` could be put on):

| Kotlin object | Python module | what |
|---|---|---|
| `KotlinSurface.SOURCE` | `python_multiplatform` | `KOTLIN_DEFAULT`, `describe`, `signature_of` -- the contract a Pythonic layer reads |
| `PythonxAdapter.SOURCE` | `python_multiplatform.binding` | the finder that serves Kotlin-named modules (`androidx.compose.*`), overload dispatch, receiver proxies |

This module reads both literals and installs them the way `PythonxAdapter.install` does. It is a
*reader*, never a copy: if either source changes, these tests exercise the changed source on the
next run.

**It installs no mapping.** The binder renames nothing; `pythonx` is this repository's own package on
disk, imported the ordinary way. Making it Pythonic is this package's job (AGENTS.md section 12).

`PythonMultiplatform` is read-only here. Nothing in this file writes to it.
"""

from __future__ import annotations

import os
import pathlib
import re
import sys
import types
from pathlib import Path

_MARKER = 'val SOURCE: String = """'

_DEFAULT_HOME = Path(__file__).resolve().parents[2] / "PythonMultiplatform"

_FFI = Path("python-multiplatform/src/commonMain/kotlin/python/multiplatform/ffi")
_ADAPTER_KT = _FFI / "pythonx" / "PythonxAdapter.kt"
_SURFACE_KT = _FFI / "upcall" / "KotlinSurface.kt"
_CALLABLES_KT = _FFI / "pythonx" / "PythonCallables.kt"

ROOT_MODULE = "python_multiplatform"
BINDING_MODULE = "python_multiplatform.binding"

_REPO = Path(__file__).resolve().parents[1]


class AdapterUnavailable(RuntimeError):
    """`PythonMultiplatform` was not found, so there is nothing to test against."""


def python_multiplatform_home() -> Path:
    """Where the binder checkout is. `PYTHONMULTIPLATFORM_HOME` overrides the sibling default."""
    override = os.environ.get("PYTHONMULTIPLATFORM_HOME")
    return Path(override).expanduser().resolve() if override else _DEFAULT_HOME


def adapter_source_path() -> Path:
    return python_multiplatform_home() / _ADAPTER_KT


def trim_indent(text: str) -> str:
    """Kotlin's `String.trimIndent`, which is what the Kotlin side applies to the literal.

    Python's `textwrap.dedent` is not the same function: it refuses to dedent when a blank line
    carries no indentation, and it does not drop the leading and trailing blank line that a
    raw-string literal always has. Getting this wrong yields a `SyntaxError` several hundred lines
    into a string nobody can see, so it is spelled out rather than approximated.
    """
    lines = text.split("\n")
    if lines and not lines[0].strip():
        lines = lines[1:]
    if lines and not lines[-1].strip():
        lines = lines[:-1]
    indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
    common = min(indents) if indents else 0
    return "\n".join(line[common:] if line.strip() else "" for line in lines)


_DOLLAR_ESCAPE = "${'$'}"
"""Kotlin's own way to put a literal `$` in a raw string without it being read as interpolation.

`SOURCE` uses this for `$composer`, `$changed` and `$default` -- Compose-compiler-synthesised
parameter names that must reach Python as `$composer` etc. Kotlin evaluates the escape before
`Python3.exec` ever sees the string; this reader has to do the same or the literal `${'$'}` text
lands in the exec'd source and every name built from it is a `SyntaxError` instead of an identifier.
"""


_INTERPOLATION = re.compile(r"\$\{(\w+)\.(\w+)\}")


def _kotlin_constant(owner: str, name: str) -> str:
    """The value of a `const val` a source literal interpolates, read from its declaring file."""
    files = {"PythonCallables": _CALLABLES_KT}
    path = python_multiplatform_home() / files.get(owner, Path("-"))
    if not path.is_file():
        raise AdapterUnavailable(f"cannot resolve ${{{owner}.{name}}}: no source for {owner}")
    found = re.search(rf'const val {name}: String = "([^"]*)"', path.read_text(encoding="utf-8"))
    if found is None:
        raise AdapterUnavailable(f"cannot resolve ${{{owner}.{name}}} in {path}")
    return found.group(1)


def _read_source(relative: Path) -> str:
    """The Python inside one `val SOURCE: String = \"\"\"...\"\"\"`, exactly as Kotlin hands it to CPython."""
    path = python_multiplatform_home() / relative
    if not path.is_file():
        raise AdapterUnavailable(
            f"{path} not found. Set PYTHONMULTIPLATFORM_HOME to the PythonMultiplatform checkout."
        )
    text = path.read_text(encoding="utf-8")
    start = text.find(_MARKER)
    if start < 0:
        raise AdapterUnavailable(f"{path} no longer declares `{_MARKER}`")
    start += len(_MARKER)
    end = text.find('"""', start)
    if end < 0:
        raise AdapterUnavailable(f"{path}: the SOURCE literal is not terminated")
    source = trim_indent(text[start:end]).replace(_DOLLAR_ESCAPE, "$")
    return _INTERPOLATION.sub(lambda m: _kotlin_constant(m.group(1), m.group(2)), source)


def read_adapter_source() -> str:
    """`PythonxAdapter.SOURCE`: the binding layer."""
    return _read_source(_ADAPTER_KT)


def read_surface_source() -> str:
    """`KotlinSurface.SOURCE`: the root module and its public contract."""
    return _read_source(_SURFACE_KT)


def read_manifest() -> dict:
    """This package's own `pythonx-map.toml`, parsed.

    The binder carries no mapping at all any more -- `pythonx.compose` means
    `androidx.compose.*` because *this* package says so, and nothing else does. Reading the real
    file rather than restating it means these tests fail if the manifest stops covering what they
    exercise, which is the only way the map and its users stay in step.
    """
    import tomllib

    path = pathlib.Path(__file__).resolve().parents[1] / "pythonx" / "compose" / "pythonx-map.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def install() -> types.ModuleType:
    """Reproduce `KotlinSurface.DELIVERY` and `PythonxAdapter.DELIVERY`; return the binding module.

    Deliberately unconditional, unlike the Kotlin, which guards on `sys.modules`. A test wants fresh
    layers per case; a running interpreter wants one per process. The caller registers a table
    (`FakeHost.register`) -- that is the generated half `PythonxAdapter.renderTable` would emit.

    The repository root goes on `sys.path` so `import pythonx.compose...` finds this package's
    files, as it would once installed.
    """
    surface, binding_source = read_surface_source(), read_adapter_source()
    uninstall()
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))
    root = types.ModuleType(ROOT_MODULE)
    root.__path__ = []
    sys.modules[ROOT_MODULE] = root
    exec(compile(surface, f"{ROOT_MODULE}/__init__.py", "exec"), root.__dict__)
    binding = types.ModuleType(BINDING_MODULE)
    sys.modules[BINDING_MODULE] = binding
    root.binding = binding
    exec(compile(binding_source, "python_multiplatform/binding.py", "exec"), binding.__dict__)
    return binding


def _owned(name: str) -> bool:
    return (
        name == ROOT_MODULE or name.startswith(ROOT_MODULE + ".")
        or name == "pythonx" or name.startswith("pythonx.")
    )


def uninstall() -> None:
    """Drop both binder layers, every module the binding layer adapted, and this package's modules.

    The Kotlin-named modules (`androidx.*`) are found through the binding layer's own `_MODULES`,
    so nothing here has to know which packages a table happened to bind. `pythonx.*` is dropped so
    the next test imports this package's files afresh against the next layer.
    """
    binding = sys.modules.get(BINDING_MODULE)
    if binding is not None:
        finder_type = getattr(binding, "_Finder", None)
        if finder_type is not None:
            sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, finder_type)]
        adapted = {module.__name__ for module in getattr(binding, "_MODULES", ())}
        seen = set(getattr(binding, "_PACKAGES_SEEN", ()))
        for name in [n for n in sys.modules if n in adapted or n in seen]:
            del sys.modules[name]
    for name in [n for n in sys.modules if _owned(n)]:
        del sys.modules[name]
