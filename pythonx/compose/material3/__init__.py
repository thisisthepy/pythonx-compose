"""`pythonx.compose.material3` -- the Pythonic view of `androidx.compose.material3`.

Every Material 3 composable (`Text`, `Button`, `Card`, `TextField`, `Checkbox`, ...) is served by
the one rule in `pythonx/compose/_reexport.py`: Kotlin's own declaration, upper-case names kept,
keyword arguments in snake_case (`on_click=`). There is no per-widget file here, on purpose
(AGENTS.md section 13). The notebook's `Column`, `Row` and `Spacer` are answered from
`pythonx.compose.layout` by the manifest's `[aliases]` (INTENT section 5.2).

## What used to be here

Per-widget wrappers from 2024 (`text.py`, `buttons.py`, `cards.py`, `icon_button.py`,
`text_field.py`, ...), each a copy of one template that looked a Kotlin function up by a
mangled-name prefix (`name.startswith("Button-")`), which Kotlin's value-class mangling makes
impossible. They were deleted as the binder rendered each declaration with no wrapper
(python-multiplatform `c60bcfeb`, `a6742a1c`, `3fde8bd6`, `cac8243f`). `icon.py` and
`color_scheme.py` were kept as records of two declarations that cannot be called yet, and 29
sibling files had always been empty; all were deleted in pythonx-compose #31. What `icon.py`
recorded -- `Icon` needs an `ImageVector` nothing bound produces -- is SPEC S5.3. `git log` on this
directory has the rest.
"""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
