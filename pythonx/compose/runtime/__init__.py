"""`pythonx/compose/runtime/__init__.py` -- the 2024 `Composable` class, gone, and what is left.

## What used to be here, and why it never ran

A decorator class (`Composable`) holding one `__composer`, plus `ComposeApp`, `KotlinComposable`,
`KotlinWidget` and a `CoroutineScope` family, all built on `jclass` --
`_runtime = jclass("io.github.thisisthepy.pycomposeui.RuntimeKt")` -- chaquopy's name-based
Java/Kotlin class lookup. `jclass` was never imported in this module, in any commit where the module
had content (`git log -p` on this file shows no `import jclass` anywhere), so every one of those five
module-level statements raised `NameError` before a single class body executed:

    >>> from pythonx.compose.runtime import Composable
    NameError: name 'jclass' is not defined

That is not incidental breakage, it is a different technology than this repository now targets.
`jclass` is chaquopy's global; `PythonMultiplatform`'s binder is a different bridge
(`docs/pythonx-adapter-design.md` §5.1, in `PythonMultiplatform`, reads the same class as "the 2024
`Composable` class", and `agent-rules.md` §12 retires name-based JVM lookup by name). The other half
of what `Composable.__call__` did -- inspecting `self.compose.__code__.co_varnames` to find where
`content` sat, so it could be popped out and wrapped specially -- is retired for the same reason
`modifier.py`'s mangled-suffix search was: `docs/pythonx-adapter-design.md` §5.6/§7 record that
composer threading, `$changed` and `$default` are now arithmetic the binder's `_bind_composable` (`python_multiplatform.binding`) does from
a slot's *declared type*, uniformly, for a `content` lambda exactly as for any other parameter. There
is nothing left for a Python-side base class to detect or thread by hand.

## What is left

One identity decorator, `Composable`, kept because `UI.ipynb` writes `@Composable` on every
screen-defining function and that surface is one an application author should keep being able to
write. Nothing needs to happen to the decorated function for it to work: the composer any nested
`pythonx.compose.*` call needs comes from the one hand-written Kotlin `@Composable`
(`PythonComposition`, in `PythonMultiplatform`) pushing it once per composition pass, and from the
*callee's* slot type deciding whether and how to thread it -- never from anything the caller does.
A plain `def Screen(): Button(...)` already works with no wrapper, no base class and no `content=`
slot detection; `@Composable` changes nothing about that and exists only so the notebook's own
spelling keeps working.

## The app root and `state`

`@app` declares the screen the host draws; `state(initial)` makes a value Compose observes. The host
is configured once with
`PythonAppView(module = "pythonx.compose.runtime", attribute = "app_root")`: it reads the module
attribute `app_root`, a Compose `MutableState` whose `.value` is a zero-argument callable or `None`
(nothing is drawn). `app(fn)` writes `app_root.value = fn` and returns `fn` unchanged, so declaring
the root again -- in a notebook cell, say -- replaces the screen. There is deliberately no update or
refresh function (`docs/INTENT.md` section 5.1).

Both states come from `_new_state`, the one place that asks the binder for
`androidx.compose.runtime.mutableStateOf`. `app_root` is created on first read, because the binder may
be installed after `pythonx` is imported. A Python object with a `.value` would not make Compose
recompose, so when the binder cannot supply `mutableStateOf` (python-multiplatform #38) `_new_state`
raises instead of falling back to one.

## How it is reached

By its own dotted name: `import pythonx.compose.runtime` loads this file. The binder used to put a
synthetic `pythonx` with `__path__ = []` into `sys.modules`, which made every file under
`pythonx/compose/` unreachable; PythonMultiplatform `d00f413f` moved its layer to
`python_multiplatform.binding` and leaves `pythonx` to this package (AGENTS.md section 12).
`tests/test_runtime_module.py::TheModuleIsTheFileOnDisk` checks that against the binder's real source.
"""

from __future__ import annotations

import sys


def Composable(target):
    """Identity. `UI.ipynb` writes `@Composable def Screen(): ...`; nothing needs to happen to
    `Screen` for that to work, because the composer every nested `pythonx.compose.*` call needs is
    threaded by `PythonComposition`/`python_multiplatform.binding._bind_composable` from the *callee's* declared slot
    type, not from anything the caller -- decorated or not -- does. See the module docstring for
    what used to be here and why it is gone.
    """
    return target



app_root: State
"""The state the host reads
(`PythonAppView(module = "pythonx.compose.runtime", attribute = "app_root")`); annotated
only, created on first read by `__getattr__` below."""


def _new_state(initial):
    """A Compose `MutableState` holding `initial`, from the binder's `mutableStateOf`.

    Never a Python stand-in: only a state Compose created is observed by composition.
    """
    try:
        import androidx.compose.runtime as kotlin_runtime

        make = kotlin_runtime.mutableStateOf
    except (ImportError, AttributeError) as missing:
        raise RuntimeError(
            "androidx.compose.runtime.mutableStateOf is not available from the binder: "
            "calling it from Python needs python-multiplatform #38"
        ) from missing
    return make(initial)


def state(initial):
    """A Compose state holding `initial`; read and write it through `.value`."""
    return _new_state(initial)


def app(root):
    """Declare `root`, a zero-argument function, as the screen the host draws; returns it unchanged.

    Declaring again replaces the screen; there is no update call.
    """
    sys.modules[__name__].app_root.value = root
    return root


from pythonx.compose._reexport import reexport

_reexported_getattr, _reexported_dir = reexport(__name__)


def __getattr__(name):
    if name == "app_root":
        created = _new_state(None)
        globals()["app_root"] = created
        return created
    return _reexported_getattr(name)


def __dir__():
    return sorted(set(_reexported_dir()) | {"app_root"})
