"""`pythonx/compose/ui/alignment.py` -- what the adaptation layer now produces, and how to spell it.

`Alignment` and its constants used to be blocked: the walker bound top-level functions and, later,
value-class constructors, and a constant held by a companion was neither. `PythonMultiplatform`'s
`80318c16` added that binding (`CallableKind.STATIC_GETTER`), and `6d896fba` proved a constant
crosses and changes a layout.

The binding exists only under its Kotlin name. Re-exporting it as `pythonx.compose.ui.Alignment` is
this package's job, not the binder's -- the earlier rule that whatever the layer produces gets no
wrapper here (`0856d08`, `f7e21f8`) was the wrong way round. Until that re-export can land, this file
records the two things a caller cannot read off the layer.

## The names the layer produces

    Bottom  BottomCenter  BottomEnd  BottomStart  Center  CenterEnd  CenterHorizontally
    CenterStart  CenterVertically  End  Start  Top  TopCenter  TopEnd  TopStart

Read out of the walked table, not from Compose's own source: a name Compose declares but the walker
declines would not be here.

## They are read, not called

    from pythonx.compose.ui import Alignment
    Alignment.Center            # no parentheses

`PythonMultiplatform`'s `46be0212` taught the layer to branch on the kind column: a static getter is
evaluated on attribute access and handed back as a value, so `Alignment.Center()` -- the spelling
this file used to prescribe -- now raises `TypeError` because the value is not callable.

`pythonx.compose.ui.Alignment` is the Kotlin object `androidx.compose.ui.Alignment` seen through the
re-export rule (`pythonx/compose/_reexport.py`, `KotlinObject`): constants keep their Kotlin
spelling and are read again on every access, as the binder serves them.

## Grouped by declared type

The notebook's grouped spelling works beside Kotlin's flat one (INTENT section 5.3):

    Alignment.Horizontal.End    # the same read as Alignment.End
    Alignment.Vertical.Top      # the same read as Alignment.Top

`Alignment.Horizontal` holds the constants declared as `Alignment.Horizontal` (`CenterHorizontally`,
`End`, `Start`) and `Alignment.Vertical` those declared as `Alignment.Vertical` (`Bottom`,
`CenterVertically`, `Top`). A constant declared as `Alignment` itself (`Center`, `TopStart`, ...) is
in neither. The grouping is the re-export rule's (`ConstantGroup`), read from the declared types
`python_multiplatform.describe(module, name)` reports without running a getter (python-multiplatform
#36), so no list here drives it.
"""
