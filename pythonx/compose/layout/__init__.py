"""`pythonx/compose/layout/__init__.py` -- the Pythonic view of `androidx.compose.foundation.layout`.

## What used to be here, and why it is gone

A try...except block executing relative import `from .arrangement import Arrangement`. `arrangement.py`
is a docstring module (no `Arrangement` class is declared inside it). Attempting to import `Arrangement`
from `.arrangement` raised `ImportError`.

## How `pythonx.compose.layout` resolves

`import pythonx.compose.layout` loads this file. The binder serves the declarations (`Arrangement`,
`Column`, `Row`, `Spacer`, ...) under their Kotlin package, `androidx.compose.foundation.layout`, and
renames nothing; re-exporting them here under Pythonic names is this package's job and has not
landed yet (SPEC section 3, issue #8).

## Calling convention for constants

Constants on layout objects (e.g., `Arrangement.Start`, `Arrangement.Center`, `Arrangement.SpaceBetween`)
are read as attributes, **without parentheses** (`Arrangement.Start`, `TextStyle.Default`), since
PythonMultiplatform `46be0212`.
"""
