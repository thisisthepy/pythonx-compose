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

## How it is reached

By its own dotted name: `import pythonx.compose.runtime` loads this file. The binder used to put a
synthetic `pythonx` with `__path__ = []` into `sys.modules`, which made every file under
`pythonx/compose/` unreachable; PythonMultiplatform `d00f413f` moved its layer to
`python_multiplatform.binding` and leaves `pythonx` to this package (AGENTS.md section 12).
`tests/test_runtime_module.py::TheModuleIsTheFileOnDisk` checks that against the binder's real source.
"""

from __future__ import annotations


def Composable(target):
    """Identity. `UI.ipynb` writes `@Composable def Screen(): ...`; nothing needs to happen to
    `Screen` for that to work, because the composer every nested `pythonx.compose.*` call needs is
    threaded by `PythonComposition`/`python_multiplatform.binding._bind_composable` from the *callee's* declared slot
    type, not from anything the caller -- decorated or not -- does. See the module docstring for
    what used to be here and why it is gone.
    """
    return target

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
