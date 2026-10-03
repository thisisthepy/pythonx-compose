"""`pythonx/compose/ui/__init__.py` -- the 2024 `from .modifier import Modifier` wrapper, unexecuted, and why.

## What used to be here, and why it never ran

A `try...except` block executing `from .modifier import Modifier`, `modifier = Modifier()`, and
`from .alignment import Alignment, AbsoluteAlignment`. `alignment.py` depended on `from java import jclass`
(Chaquopy-era JVM class lookup, retired in this codebase).

## How `pythonx.compose.ui` resolves

`import pythonx.compose.ui` loads this file; it is an ordinary package on disk. The binder serves the
Kotlin package under its Kotlin name, `androidx.compose.ui`, as a separate module, and renames
nothing. This file re-exports it under Pythonic names (`Modifier`, `describe_modifier`, ...) by the
one rule in `pythonx/compose/_reexport.py` (SPEC section 3); it names no declaration itself.
"""

from __future__ import annotations

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
