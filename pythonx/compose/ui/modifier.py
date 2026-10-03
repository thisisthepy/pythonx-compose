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

## What is left, and why it cannot be derived

One fact, and it is data rather than code: **the name of a Kotlin function that returns an empty
`Modifier`.**

`Modifier` as a Kotlin *expression* is `Modifier.Companion`, an object instance, and the artefact
walker binds functions. So the empty modifier every chain starts from has **no bound name**, and the
adaptation layer refuses to invent one -- `Modifier.padding(16)` raises a `TypeError` naming
`register_empty` rather than guessing. Registering that name is the seam, and this file is it.

**No such function exists in Compose today.** `androidx.compose.ui.emptyModifier` is the name
`ComposeShapedFragment` uses for the fixture, and it is a placeholder: against the real jars nothing
is bound under it, so the class-object spelling does not yet work and only the instance spelling
(`m.padding(16)`, on a `Modifier` Kotlin handed out) does. Closing that needs one line of Kotlin in
the consuming application -- `fun emptyModifier(): Modifier = Modifier`, picked up by KSP -- and
[install] is where its name is supplied.

## How this module is reached

As `pythonx.compose.ui.modifier`, an ordinary module of this package. It needs the binder's layer
(`python_multiplatform.binding`) to be installed by the host before [install] can do anything.
"""

from __future__ import annotations

import importlib
import sys

BINDING_MODULE = "python_multiplatform.binding"

KOTLIN_PACKAGE = "androidx.compose.ui"

KOTLIN_TYPE = KOTLIN_PACKAGE + ".Modifier"
"""The Kotlin type the proxy stands for. The walker reports it as `receiverTypeName`."""

PLACEHOLDER_EMPTY_FACTORY = "androidx.compose.ui.emptyModifier"
"""A name that is **not** bound by Compose. See the module docstring; supply your own to [install]."""


def adapter():
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
    return module


def modifier_type(layer=None):
    """The `Modifier` proxy class -- the same object `pythonx.compose.ui.Modifier` is."""
    if layer is None:
        adapter()
    # Through this package's own module, so the manifest's value-class allowlist is in force.
    return importlib.import_module("pythonx.compose.ui").Modifier


def install(empty_factory=PLACEHOLDER_EMPTY_FACTORY, layer=None):
    """Register where an empty `Modifier` comes from, and return the proxy class.

    :param empty_factory: the fully-qualified Kotlin name of a zero-argument function returning
        `Modifier`. Must be bound in the upcall table; nothing in Compose is, so this is normally a
        one-line function in the consuming application's own Kotlin.
    :param layer: the adaptation layer, for tests that hold one directly.
    """
    layer = layer or adapter()
    layer.register_empty(KOTLIN_TYPE, empty_factory)
    return modifier_type(layer)


def __getattr__(name):
    # `Modifier` is resolved rather than defined, so that this module cannot hold a stale class
    # across a table reinstall -- `_register_table` invalidates every proxy, and a module-level
    # binding made at import time would outlive that.
    if name == "Modifier":
        return modifier_type()
    raise AttributeError(name)
