"""`pythonx/compose/ui/__init__.py` -- the 2024 `from .modifier import Modifier` wrapper, unexecuted, and why.

## What used to be here, and why it never ran

A `try...except` block executing `from .modifier import Modifier`, `modifier = Modifier()`, and
`from .alignment import Alignment, AbsoluteAlignment`. `alignment.py` depended on `from java import jclass`
(Chaquopy-era JVM class lookup, retired in this codebase).

## How `pythonx.compose.ui` resolves

`import pythonx.compose.ui` loads this file; it is an ordinary package on disk. The binder serves the
Kotlin package under its Kotlin name, `androidx.compose.ui`, as a separate module, and renames
nothing. Re-exporting its declarations here under Pythonic names (`Modifier`, `Alignment`, ...) is
this package's job and has not landed yet (SPEC section 3, issue #8). Until then this file carries
no code.
"""

from __future__ import annotations
