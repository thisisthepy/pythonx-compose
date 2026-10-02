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

    from androidx.compose.ui import Alignment
    Alignment.Center            # no parentheses

`PythonMultiplatform`'s `46be0212` taught the layer to branch on the kind column: a static getter is
evaluated on attribute access and handed back as a value, so `Alignment.Center()` -- the spelling
this file used to prescribe -- now raises `TypeError` because the value is not callable.

The import is the Kotlin name on purpose. The binder no longer re-exports anything under
`pythonx.*`; giving these a `pythonx.compose.ui` spelling is this package's job, and until the
adapter stops occupying `sys.modules['pythonx']` that re-export has nowhere to live.
"""
