"""`pythonx.compose.material` -- the Pythonic view of `androidx.compose.material` (see `pythonx/compose/_reexport.py`).

Material 2's own composables are not bound; this package is here for `material.icons`.
"""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
