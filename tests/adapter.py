"""Load the `pythonx` adaptation layer that lives in `PythonMultiplatform`.

The adapter is **not** a `.py` file. `PythonxAdapter.kt` holds it as a Kotlin raw-string literal and
`Python3.exec`s it at run time, for the reason its KDoc gives: on iOS, androidNative and wasm there
is no resource path a `.py` could be put on. `docs/pythonx-adapter-design.md` §2.5 records that as
open.

That leaves this repository unable to `import pythonx` the ordinary way, and unable to test against
the layer it is supposed to sit on -- unless it reads the layer out of the Kotlin literal. That is
what this module does. It is a *reader*, never a copy: if `PythonxAdapter.SOURCE` changes, these
tests exercise the changed source on the next run, so the two cannot drift.

`PythonMultiplatform` is read-only here. Nothing in this file writes to it.
"""

from __future__ import annotations

import os
import pathlib
import sys
import types
from pathlib import Path

_MARKER = 'val SOURCE: String = """'

_DEFAULT_HOME = Path(__file__).resolve().parents[2] / "PythonMultiplatform"

_ADAPTER_KT = Path(
    "python-multiplatform/src/commonMain/kotlin/python/multiplatform/ffi/pythonx/PythonxAdapter.kt"
)


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


def read_adapter_source() -> str:
    """The Python inside `PythonxAdapter.SOURCE`, exactly as Kotlin would hand it to CPython."""
    path = adapter_source_path()
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
    return trim_indent(text[start:end]).replace(_DOLLAR_ESCAPE, "$")


def read_manifest() -> dict:
    """This package's own `pythonx-map.toml`, parsed.

    The binder carries no mapping at all any more -- `pythonx.compose` means
    `androidx.compose.*` because *this* package says so, and nothing else does. Reading the real
    file rather than restating it means these tests fail if the manifest stops covering what they
    exercise, which is the only way the map and its users stay in step.
    """
    import tomllib

    path = pathlib.Path(__file__).resolve().parents[1] / "pythonx-map.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def install(source: str | None = None) -> types.ModuleType:
    """Reproduce `PythonxAdapter.DELIVERY`: build the `pythonx` module and exec the source into it.

    Deliberately unconditional, unlike the Kotlin, which guards on `sys.modules`. A test wants a
    fresh layer per case; a running interpreter wants one per process.

    The manifest is applied here because an embedder applies it there: `PythonxAdapter.install`
    takes the map as an argument and registers nothing without one. A fake host that skipped this
    step would be testing a layer no real caller runs.
    """
    uninstall()
    module = types.ModuleType("pythonx")
    module.__path__ = []
    sys.modules["pythonx"] = module
    exec(compile(source or read_adapter_source(), "pythonx/__init__.py", "exec"), module.__dict__)
    manifest = read_manifest()
    for python_name, kotlin_package in manifest["modules"].items():
        module.register_package(python_name, kotlin_package)
    for kotlin_type in manifest["value-classes"]["raw-primitive-allowed"]:
        module.allow_raw_primitive(kotlin_type)
    return module


def uninstall() -> None:
    """Drop `pythonx` and everything under it, and take the finder back off `sys.meta_path`."""
    adapter = sys.modules.get("pythonx")
    if adapter is not None:
        finder_type = getattr(adapter, "_Finder", None)
        if finder_type is not None:
            sys.meta_path[:] = [f for f in sys.meta_path if not isinstance(f, finder_type)]
    for name in [n for n in sys.modules if n == "pythonx" or n.startswith("pythonx.")]:
        del sys.modules[name]
