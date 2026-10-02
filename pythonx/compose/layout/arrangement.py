"""`pythonx/compose/layout/arrangement.py` -- what the adaptation layer now produces, and how to spell it.

The same story as `pythonx/compose/ui/alignment.py`, and the same two facts. `Arrangement`'s constants
are bound by the walker since `PythonMultiplatform`'s `80318c16`, and `6d896fba` is the proof: the
same child in the same row lands at opposite edges under `Start` and `End`, which is what says the
value crossed rather than that something merely composed.

## The names the layer produces

    Bottom  Center  End  SpaceAround  SpaceBetween  SpaceEvenly  Start  Top

Read out of the walked table. Compose declares more (`spacedBy`, for one) -- those are functions
rather than constants and reach Python through the ordinary function path, not this one.

## They are read, not called

    from androidx.compose.foundation.layout import Row, Arrangement, width__Dp
    from androidx.compose.material3 import Text
    from fixture.compose import emptyModifier

    Row(
        modifier=width__Dp(emptyModifier(), 80.0),
        horizontal_arrangement=Arrangement.End,        # no parentheses
        content=lambda scope: Text('X'),
    )

Since upstream's `46be0212` a static getter is evaluated on attribute access, so `Arrangement.End()`
raises `TypeError` -- the value is not callable. The imports are the Kotlin names for the reason
`alignment.py` gives.

The width matters as much as the spelling: a row wraps its content, so with no width constraint
there is no spare space and every arrangement puts the child in the same place. Upstream's proof
passed for that wrong reason once, before its opposite-end control caught it.
"""
