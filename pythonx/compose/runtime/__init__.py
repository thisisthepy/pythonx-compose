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

## The app root

`@app` declares the screen the host draws. The host is configured once with
`PythonAppView(module = "pythonx.compose.runtime", attribute = "app_root")`: it reads the module
attribute `app_root`, a Compose `MutableState` whose `.value` is a zero-argument callable or `None`
(nothing is drawn). `app(fn)` writes `app_root.value = fn` and returns `fn` unchanged, so declaring
the root again -- in a notebook cell, say -- replaces the screen. There is deliberately no update or
refresh function (`docs/INTENT.md` section 5.1).

`app_root` comes from `_new_state`, the internal function that asks the binder for
`androidx.compose.runtime.mutableStateOf`; it is created on first read, because the binder may be
installed after `pythonx` is imported. A screen's own state is not a name of this package: it is
Kotlin's `mutable_state_of`, re-exported by the rule, or `remember_saveable` (`docs/INTENT.md`
sections 5.9 and 5.11; the former `state()` is removed, issue #101). A Python object with a `.value`
would not make Compose recompose, so when the binder cannot supply `mutableStateOf`
(python-multiplatform #38) `_new_state` raises instead of falling back to one.

## `remember_saveable`

`remember_saveable(initial)` is Compose's `rememberSaveable`: the value survives recomposition,
rotation and process restart (`docs/INTENT.md` section 5.9). It calls the host's `@Composable`
`python.multiplatform.compose.rememberSaveableWrapper(initial)` (python-multiplatform #174), which
picks the Kotlin state from the value's type (Int, Long, Double, Boolean, String) and refuses any
other, as pycomposeui's wrapper of that name did. The value is passed as it is; the type rule is
Kotlin's alone. Like any composable, it works only inside a composition.

It returns a `SaveableState`, a thin wrapper over that Kotlin `MutableState`, with the notebook's
`getValue()` / `setValue(value)` (cells 9 to 13) and `.value` as the Pythonic alias. Every read goes
through `MutableState.value`, so Compose records the read and recomposes on a write; nothing is
cached here. The app attaches the state to its root itself, as the 2024 demo did
(`App.messages = messages = remember_saveable("")` inside `def App():`), which is how
`main.App.messages` exists; there is no lookup by variable name.

A host app binds the wrapper by listing `python.multiplatform.compose.RememberSaveableKt` in its
`artifactIncludePackages`.

## How it is reached

By its own dotted name: `import pythonx.compose.runtime` loads this file. The binder used to put a
synthetic `pythonx` with `__path__ = []` into `sys.modules`, which made every file under
`pythonx/compose/` unreachable; PythonMultiplatform `d00f413f` moved its layer to
`python_multiplatform.binding` and leaves `pythonx` to this package (AGENTS.md section 12).
`tests/test_runtime_module.py::TheModuleIsTheFileOnDisk` checks that against the binder's real source.
"""

from __future__ import annotations

import importlib
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


def app(root):
    """Declare `root`, a zero-argument function, as the screen the host draws; returns it unchanged.

    Declaring again replaces the screen; there is no update call.
    """
    sys.modules[__name__].app_root.value = root
    return root


_SAVEABLE_HOST = "python.multiplatform.compose"


class SaveableState:
    """What `remember_saveable` returns: the notebook's `getValue()` / `setValue(value)` over a
    Compose `MutableState`, with `.value` as the Pythonic alias. Holds nothing but the state."""

    __slots__ = ("_state",)

    def __init__(self, state):
        self._state = state

    def getValue(self):
        """The current value, read from the Kotlin state (a snapshot read Compose records)."""
        return self._state.value

    def setValue(self, value):
        """Write the Kotlin state; a composable that read it recomposes."""
        self._state.value = value

    @property
    def value(self):
        return self._state.value

    @value.setter
    def value(self, value):
        self._state.value = value

    def __repr__(self):
        return f"SaveableState({self._state.value!r})"


def remember_saveable(initial: bool | int | float | str) -> SaveableState:
    """Compose's `rememberSaveable` for an int, float, bool or str; call it inside a composition."""
    try:
        wrapper = importlib.import_module(_SAVEABLE_HOST).rememberSaveableWrapper
    except (ImportError, AttributeError) as missing:
        raise RuntimeError(
            f"{_SAVEABLE_HOST}.rememberSaveableWrapper is not bound: it needs python-multiplatform #174, "
            "and the host app must list python.multiplatform.compose.RememberSaveableKt in "
            "artifactIncludePackages"
        ) from missing
    return SaveableState(wrapper(initial))


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
