"""`pythonx.compose.material.icons` -- the Pythonic view of `androidx.compose.material.icons` (see `pythonx/compose/_reexport.py`).

`Icons.Default.Add` is served by the rule; `material3` lends `Icons.Default` as `DefaultIcons`
(`[aliases]` in `pythonx-map.toml`, INTENT section 5.7).
"""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
