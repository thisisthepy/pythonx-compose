"""Where a `Modifier` chain starts -- and the only thing about `Modifier` that is hand-written.

## What used to be here

A copy of the Button wrapper. `padding()` composed nothing, `fill_max_size()` returned `self`, and
lines 20-22 searched `ButtonKt.__dict__` for a name beginning `"Button-"` -- a prefix search over
Kotlin's value-class mangling suffix. That search is not merely broken, it is *impossible*: the
suffix hashes the value-class signature only, so `padding`, `size`, `width` and `height` all mangle
to `-3ABfNKs` and a name lookup cannot tell them apart. Looking a Kotlin declaration up by JVM name
is a removed option (`agent-rules.md` §12); the binder generates Kotlin source and lets `kotlinc`
mangle it.

## What replaced it, and where that lives

Not here. `Modifier` is an ordinary proxy the binder builds from the upcall table and serves as
`androidx.compose.ui.Modifier`; `pythonx.compose.ui.Modifier` is that same class, re-exported by
the naming rule in `pythonx/compose/_reexport.py`.
Every one of its methods is a `Modifier` extension the artefact walker bound out of Compose's own
jars -- 104 of them at last count (`docs/kotlin-extensions-in-python.md` §3.2) -- and each is
attached to the proxy type on first read and never resolved again. So:

    Modifier.padding(16).size(24)          # chained, with zero hand-written wrappers
    padding(m, horizontal=8, vertical=4)   # dispatched among four `padding` overloads

None of that is per-declaration Python, which is exactly why none of it is a file
(`docs/pythonx-adapter-design.md` §7). **If this file ever grows a `def padding`, the 2024 mistake
has been made again.**

## What is left, and how the empty `Modifier` is reached

`Modifier` as a Kotlin *expression* is `Modifier.Companion`, an object instance. Since
python-multiplatform #324 (`ba338d4f`, closing #322), a public companion object is bound as a
`STATIC_GETTER` (`androidx.compose.ui.Modifier.Companion`, typed as `Modifier`) and read on the
owner's proxy class as `Modifier.Companion`, while `register_empty` accepts the proxy class and a
Python callable (`register_empty(Modifier, lambda: Modifier.Companion)`).

`pythonx.compose._reexport._prime` registers that callable by default on first resolution of a
`pythonx.compose` module, and [install] with no argument registers the same
`register_empty(Modifier, lambda: Modifier.Companion)` (`SPEC.md` S6.2, #138). Both the class-object
chain (`Modifier.padding(16)`) and passing `Modifier` as an argument (`Card(modifier=Modifier)`,
`Spacer(modifier=Modifier)`) therefore evaluate `Modifier.Companion` out of the box against real
Compose, with no application-supplied Kotlin `emptyModifier` helper needed. [install] still accepts
an explicit Kotlin function name or callable when a test or host overrides the default.

## How this module is reached

As `pythonx.compose.ui.modifier`, an ordinary module of this package. It needs the binder's layer
(`python_multiplatform.binding`) to be installed by the host before [install] can do anything.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable
from typing import Protocol, cast

BINDING_MODULE = "python_multiplatform.binding"

KOTLIN_PACKAGE = "androidx.compose.ui"

KOTLIN_TYPE = KOTLIN_PACKAGE + ".Modifier"
"""The Kotlin type the proxy stands for. The walker reports it as `receiverTypeName`."""

PLACEHOLDER_EMPTY_FACTORY = "androidx.compose.ui.emptyModifier"
"""A name that is **not** bound by Compose. Kept for fixture tests; [install] defaults to `Modifier.Companion`."""


class BindingLayer(Protocol):
    """What this module asks of `python_multiplatform.binding`."""

    def register_empty(self, kotlin_type: object, empty_factory: str | Callable[[], object], /) -> None: ...


def adapter() -> BindingLayer:
    """The binder's installed binding layer, or a `RuntimeError` that says what did not happen.

    The Kotlin host installs it (`PythonxAdapter.install()`), not an import, so its absence means
    the host never ran it -- a different failure from a missing package, with a different message.
    """
    module = sys.modules.get(BINDING_MODULE)
    if module is None or not hasattr(module, "register_empty"):
        raise RuntimeError(
            "the python-multiplatform binding layer is not installed: the Kotlin host must run "
            "PythonxAdapter.install() before anything here can resolve a Modifier"
        )
    return cast(BindingLayer, module)


def modifier_type(layer: BindingLayer | None = None) -> type[object]:
    """The `Modifier` proxy class -- the same object `pythonx.compose.ui.Modifier` is."""
    if layer is None:
        adapter()
    # Through this package's own module, so the manifest's value-class allowlist is in force.
    return cast("type[object]", importlib.import_module("pythonx.compose.ui").Modifier)


def _modifier_companion() -> object:
    """`Modifier.Companion` read live from `androidx.compose.ui.Modifier` (python-multiplatform #324)."""
    return cast(object, importlib.import_module("androidx.compose.ui").Modifier.Companion)


def install(
    empty_factory: str | Callable[[], object] | None = None,
    layer: BindingLayer | None = None,
) -> type[object]:
    """Register where an empty `Modifier` comes from, and return the proxy class.

    :param empty_factory: a zero-argument callable returning an empty `Modifier` (defaults to
        `lambda: Modifier.Companion`, python-multiplatform #324), or the fully-qualified Kotlin name
        of a zero-argument function returning `Modifier`.
    :param layer: the adaptation layer, for tests that hold one directly.
    """
    layer = layer or adapter()
    cls = modifier_type(layer)
    layer.register_empty(cls, _modifier_companion if empty_factory is None else empty_factory)
    return cls


def __getattr__(name: str) -> type[object]:
    # `Modifier` is resolved rather than defined, so that this module cannot hold a stale class
    # across a table reinstall -- `_register_table` invalidates every proxy, and a module-level
    # binding made at import time would outlive that.
    if name == "Modifier":
        return modifier_type()
    raise AttributeError(name)
