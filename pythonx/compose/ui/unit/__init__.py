"""`pythonx/compose/ui/unit/__init__.py` -- unit declarations provided by the adaptation layer.

## What used to be here, and why it is gone

A relative import `from .dp import dp`. `dp.py` was an empty file.

## Dynamic unit handling

A raw number reaches a `Dp` parameter because `pythonx-map.toml` allows it and the re-export rule
hands that allowlist to the binder (`pythonx/compose/_reexport.py`). An explicit `Dp` value is
`python_multiplatform.binding.value_of('androidx.compose.ui.unit.Dp', 16)`; a short `dp()` spelling
is not provided yet.
"""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
