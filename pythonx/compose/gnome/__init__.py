"""`pythonx.compose.gnome`: the Pythonic view of `org.thisisthepy.compose.gnome`, GNOME (`GnomeDesignSystem`).

From the fork `compose-multiplatform-core-extended`, `extended/design-systems/gnome`, exposed by the
owner's decision of 2026-11-13 (#54, #152). Served by the one rule in `pythonx/compose/_reexport.py`:
Kotlin's own declarations, upper-case names kept, keyword arguments in snake_case. Nothing is
written here by hand.

The design systems are not on Maven Central yet, so the binder serves no `org.thisisthepy.compose.gnome` and every
name read here raises `AttributeError` until python-multiplatform walks the published artefact. Its
stub is empty until then, and `tests/test_design_systems.py` fails the day it is not, until its
surface snapshot is recorded (`scripts/surface.py`).
"""

from pythonx.compose._reexport import reexport

__getattr__, __dir__ = reexport(__name__)
