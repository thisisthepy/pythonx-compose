"""`pythonx.compose.foundation` -- the Pythonic view of `androidx.compose.foundation` (see `pythonx/compose/_reexport.py`)."""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
