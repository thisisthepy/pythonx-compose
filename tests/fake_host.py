"""A stand-in for the Kotlin host: `_pm_resolve`, `_pm_invoke`, `_pm_release`, and a table.

The three names in `__main__` are the *whole* Python-facing surface of the binder
(`docs/pythonx-adapter-design.md` §2.4). Everything `pythonx` does above them -- the finder, the
name rule, the overload dispatcher, the receiver proxies -- is Python, so all of it can be exercised
without a JVM, an emulator or a `Composer`, provided something answers those three names.

**The table is a transcription of `ComposeShapedFragment.kt`**, entry for entry, name for name,
including `<receiver>` in slot 0 and `paramHasDefault`. That fixture is itself pinned against the
real walked `androidx.compose.foundation.layout.padding__Dp` by
`PythonxAdapterTest.shapeMatchesTheWalkedEntries`, so these rows are the shape the artefact walker
actually produces out of `foundation-layout-desktop-1.6.11.jar` -- not a convenient simplification.

**The state rows are shaped after python-multiplatform `31c092f0` (#38), not transcribed from a
walked jar.** `KotlinSurface.kt` (the describe docs) and `PythonxAdapter.kt` (`_register_table`,
`_read_property`, `_write_property`, `_coerce`) define them, and the fields modelled are:
`androidx.compose.runtime.mutableStateOf` -- `kind` FUNCTION, one slot `value` tagged OBJECT
declared `kotlin.Any` (an unbounded type parameter, the spelling `_KOTLIN_ANY` reads), returning an
OBJECT of `androidx.compose.runtime.MutableState`; `androidx.compose.runtime.MutableState.value` --
`kind` GETTER, arity 0, `receiver_type_name` `MutableState` (the receiver is *not* a slot, but the
adapter sends its handle in `args[0]`), returning OBJECT `kotlin.Any`; and
`androidx.compose.runtime.MutableState.value=` -- `kind` SETTER, whose leaf ends in `=`, one slot
`value` OBJECT `kotlin.Any`, returning `kotlin.Unit`. A `kotlin.Any` slot carries a Python object as
itself and a Kotlin object as its handle, as `_coerce` does; the stub keeps the Python object.
No walked row for these exists in this repository, so the shape is only as faithful as that reading.

**The text-field rows are shaped after the stubs, not a walked jar** (python-multiplatform `26485a02`,
which includes #73; the `kotlin-stubs` artefact's `androidx/compose/foundation/text/input/__init__.pyi`
and the TextField overloads of `androidx/compose/material3/__init__.pyi`). Modelled:
`TextFieldState__String_TextRange` (the constructor, named like a constructor-shaped function, both
slots defaulted, returning OBJECT `TextFieldState`); `rememberTextFieldState` (a `@Composable`:
`initialText`, `initialSelection`, then `$composer`, `$changed`, `$default` -- the slot names
`PythonxAdapter` reads as the composable flag); `TextFieldState.text` (GETTER, receiver in `args[0]`,
returning STRING declared `kotlin.CharSequence`, which the stub types `str`);
`setTextAndPlaceCursorAtEnd` and `clearText` (FUNCTION, extension, `<receiver>` slot 0 typed
`TextFieldState`, as the stub's module functions take `receiver, /`); and two `TextField`
overloads, `TextField__TextFieldState` (`state`, `modifier`, `enabled`, `readOnly`, `isError`, composable)
and `TextField__String` (`value`, `modifier`, composable). Those two keep a subset of the real
parameters: `label` and `onValueChange` are function-typed slots, and a function slot needs the
binder's `NewFunction` rows, which this host does not carry. Neither draws; a call is logged in
`composable_calls`. `TextRange` is an opaque OBJECT here; the binder's #78 caveat (a companion
module shadowing `TextRange(2)`) is not modelled.

What this does **not** prove: that the Kotlin half marshals correctly, that Compose's own `padding`
runs, or that a handle is released on the Kotlin side. Those are
`WalkedArtifactComposeModifierTest` and `PythonxAdapterTest`, and they live in the other repository
because they need a classpath. What is proved here is the Python half, which is where every line of
`pythonx` is.
"""

from __future__ import annotations

import sys

MODIFIER = "androidx.compose.ui.Modifier"
DP = "androidx.compose.ui.unit.Dp"
PADDING_VALUES = "androidx.compose.foundation.layout.PaddingValues"
TEXT_UNIT = "androidx.compose.ui.unit.TextUnit"

ARRANGEMENT = "androidx.compose.foundation.layout.Arrangement"
ARRANGEMENT_HORIZONTAL = ARRANGEMENT + ".Horizontal"
ARRANGEMENT_VERTICAL = ARRANGEMENT + ".Vertical"
ARRANGEMENT_BOTH = ARRANGEMENT + ".HorizontalOrVertical"
ALIGNMENT = "androidx.compose.ui.Alignment"
COLOR = "androidx.compose.ui.graphics.Color"
# python-multiplatform-compose, the host module (python-multiplatform #18, #174).
COMPOSE_HOST = "python.multiplatform.compose"
ALIGNMENT_HORIZONTAL = ALIGNMENT + ".Horizontal"
ALIGNMENT_VERTICAL = ALIGNMENT + ".Vertical"

KOTLIN_ANY = "kotlin.Any"
RUNTIME = "androidx.compose.runtime"
MUTABLE_STATE = RUNTIME + ".MutableState"

ICONS_PACKAGE = "androidx.compose.material.icons"
ICONS = ICONS_PACKAGE + ".Icons"
ICONS_FILLED = ICONS + ".Filled"
IMAGE_VECTOR = "androidx.compose.ui.graphics.vector.ImageVector"

TEXT_INPUT = "androidx.compose.foundation.text.input"
TEXT_FIELD_STATE = TEXT_INPUT + ".TextFieldState"
TEXT_RANGE = "androidx.compose.ui.text.TextRange"
MATERIAL3 = "androidx.compose.material3"

EMPTY_MODIFIER = "androidx.compose.ui.emptyModifier"
"""The one entry the real walker does **not** produce; see `ComposeShapedFragment.EMPTY_MODIFIER`.

`Modifier` as an expression is `Modifier.Companion`, an object, and the walker binds functions. So
against real Compose there is no bound name for the empty modifier and the class-object spelling
`Modifier.padding(16)` has nothing to start from. Keeping the fixture's name here keeps that fact
visible rather than papering over it.
"""


class StubModifier:
    """What a `Modifier` is for this fixture: the ordered list of what was applied to it."""

    __slots__ = ("elements",)

    def __init__(self, elements=()):
        self.elements = tuple(elements)

    def plus(self, element):
        return StubModifier(self.elements + (element,))

    def describe(self):
        return " -> ".join(self.elements) if self.elements else "<empty>"


class StubConstant:
    """What an object constant is for this fixture: its name, so a test can see which one arrived."""

    __slots__ = ("label",)

    def __init__(self, label):
        self.label = label


class StubIconSet:
    """`Icons.Filled`: the one object `Icons.Default` resolves to, so a test can tell it was reached."""

    __slots__ = ()


class StubTextFieldState:
    """A `TextFieldState` for this fixture: the committed text, which is all Python ever reads."""

    __slots__ = ("text",)

    def __init__(self, text=""):
        self.text = text


class StubPaddingValues:
    """An ordinary object parameter, so two arity-2 overloads differ by declared type alone."""

    __slots__ = ("label",)

    def __init__(self, label):
        self.label = label


class StubState:
    """A `MutableState` for this fixture: one value, and a log of what was written to it."""

    __slots__ = ("value", "writes")

    def __init__(self, value):
        self.value = value
        self.writes = [value]

    def write(self, value):
        self.value = value
        self.writes.append(value)


def _dp(value):
    # `ComposeShapedFragment.dp` is `(value as Double).toString()`, so 16 renders as "16.0".
    return str(float(value))


class FakeHost:
    """Owns the entry table, the handle table, and the call log."""

    def __init__(self):
        self.calls = []
        self.released = []
        self._entries = {}
        self._order = []
        self._handles = {}
        self._next_handle = 1
        self.filled = StubIconSet()
        self.composable_calls = []
        self.last_text_field_flags = None
        self.last_text_field_modifier = None
        self.saveable_calls = []
        self._composer = None
        self._build()

    # ------------------------------------------------------------------ the boundary (3 names)

    def resolve(self, name_bytes):
        name = name_bytes.decode("utf-8") if isinstance(name_bytes, bytes) else name_bytes
        if name not in self._entries:
            return -1
        return self._order.index(name)

    def invoke(self, handle, args):
        name = self._order[handle]
        row, body = self._entries[name]
        tags = row[5]
        property_row = row[2] in ("GETTER", "SETTER")
        # A property's receiver is not one of its slots (`CallableKind.GETTER`): its handle is
        # `args[0]` and the declared slots follow it.
        slots = args[1:] if property_row else args
        unpacked = [
            self._unpack(value, tags[index], row[6][index]) for index, value in enumerate(slots)
        ]
        if property_row:
            unpacked.insert(0, self._object(args[0]))
        result = body(unpacked)
        if row[7] == "OBJECT":
            if row[8] is None:
                return result  # `unboxScalar`: a Python scalar or None, never a handle
            if row[8] != KOTLIN_ANY:
                return self._handle(result)
            if isinstance(result, (bool, int, float, str)):
                # A scalar held in a `kotlin.Any` is a Kotlin box, so it crosses as a handle and the
                # binding layer unboxes it through `unboxScalar` (python-multiplatform #69).
                return self._handle(result)
        return result

    def _unpack(self, value, tag, type_name):
        if tag != "OBJECT" or value is None:
            return value  # a null reference crosses as None
        if type_name == KOTLIN_ANY and not self._is_handle(value):
            return value  # a Python object crossing an `Any?` slot as itself
        return self._object(value)

    def _is_handle(self, value):
        return isinstance(value, int) and not isinstance(value, bool) and value in self._handles

    def release(self, handle):
        self.released.append(handle)
        self._handles.pop(handle, None)
        return 0

    def bind(self):
        """Publish the three names in `__main__`, where `pythonx._boundary()` looks for them."""
        main = sys.modules["__main__"]
        main._pm_resolve = self.resolve
        main._pm_invoke = self.invoke
        main._pm_release = self.release

    def unbind(self):
        main = sys.modules["__main__"]
        for name in ("_pm_resolve", "_pm_invoke", "_pm_release"):
            if hasattr(main, name):
                delattr(main, name)

    def rows(self):
        """The 12-tuples `PythonxAdapter.renderTable` emits, in table order."""
        return tuple(self._entries[name][0] for name in self._order)

    def register(self, adapter):
        adapter._register_table(self.rows())

    # ------------------------------------------------------------------ handles

    def _handle(self, obj):
        handle = self._next_handle
        self._next_handle += 1
        self._handles[handle] = obj
        return handle

    def _object(self, handle):
        if handle not in self._handles:
            raise AssertionError(f"no live handle {handle!r}")
        return self._handles[handle]

    def composer(self):
        """A handle standing in for the `Composer` a composition would push (`push_composer`)."""
        if self._composer is None:
            self._composer = self._handle(object())
        return self._composer

    def live_handles(self):
        return set(self._handles)

    # ------------------------------------------------------------------ the table

    def _add(self, name, arity, param_names, param_tags, param_type_names, return_tag,
             return_type_name, is_extension, receiver_type_name, param_has_default, body,
             kind="FUNCTION"):
        row = (
            name, arity, kind, False, tuple(param_names), tuple(param_tags),
            tuple(param_type_names), return_tag, return_type_name, is_extension,
            receiver_type_name, tuple(param_has_default),
        )
        self._entries[name] = (row, body)
        self._order.append(name)

    def _extension(self, name, param_names, param_tags, param_type_names, param_has_default, body):
        # Slot 0 spelled the way the walker spells it: counted in arity, named `<receiver>`, typed
        # with the receiver's Kotlin type name, never defaulted.
        self._add(
            name=name,
            arity=len(param_tags) + 1,
            param_names=("<receiver>",) + tuple(param_names),
            param_tags=("OBJECT",) + tuple(param_tags),
            param_type_names=(MODIFIER,) + tuple(param_type_names),
            return_tag="OBJECT",
            return_type_name=MODIFIER,
            is_extension=True,
            receiver_type_name=MODIFIER,
            param_has_default=(False,) + tuple(param_has_default),
            body=lambda args: body(args[0], args[1:]),
        )

    def _logged(self, label, render):
        def body(receiver, args):
            self.calls.append(label)
            return receiver.plus(render(args))

        return body

    def _build(self):
        self._scalar_boxes()
        self._build_text_field()
        self._build_color()
        self._build_saveable()
        self._add(
            EMPTY_MODIFIER, 0, (), (), (), "OBJECT", MODIFIER, False, None, (),
            lambda args: StubModifier(),
        )
        self._add(
            "androidx.compose.ui.describeModifier", 1, ("modifier",), ("OBJECT",), (MODIFIER,),
            "STRING", "kotlin.String", False, None, (False,),
            lambda args: args[0].describe(),
        )
        self._extension(
            "androidx.compose.foundation.layout.padding__Dp",
            ("all",), ("FLOAT",), (DP,), (False,),
            self._logged("padding__Dp", lambda a: f"padding({_dp(a[0])})"),
        )
        self._extension(
            "androidx.compose.foundation.layout.padding__Dp_Dp",
            ("horizontal", "vertical"), ("FLOAT", "FLOAT"), (DP, DP), (True, True),
            self._logged("padding__Dp_Dp", lambda a: f"padding(h={_dp(a[0])}, v={_dp(a[1])})"),
        )
        self._extension(
            "androidx.compose.foundation.layout.padding__Dp_Dp_Dp_Dp",
            ("start", "top", "end", "bottom"), ("FLOAT",) * 4, (DP,) * 4, (True,) * 4,
            self._logged(
                "padding__Dp_Dp_Dp_Dp",
                lambda a: (
                    f"padding(s={_dp(a[0])}, t={_dp(a[1])}, "
                    f"e={_dp(a[2])}, b={_dp(a[3])})"
                ),
            ),
        )
        self._extension(
            "androidx.compose.foundation.layout.padding__PaddingValues",
            ("paddingValues",), ("OBJECT",), (PADDING_VALUES,), (False,),
            self._logged("padding__PaddingValues", lambda a: f"padding({a[0].label})"),
        )
        self._add(
            "androidx.compose.foundation.layout.paddingValuesOf", 1, ("all",), ("FLOAT",), (DP,),
            "OBJECT", PADDING_VALUES, False, None, (False,),
            lambda args: StubPaddingValues(f"pv({_dp(args[0])})"),
        )
        self._extension(
            "androidx.compose.foundation.layout.size__Dp",
            ("size",), ("FLOAT",), (DP,), (False,),
            self._logged("size__Dp", lambda a: f"size({_dp(a[0])})"),
        )
        self._extension(
            "androidx.compose.foundation.layout.fillMaxWidth",
            (), (), (), (),
            self._logged("fillMaxWidth", lambda a: "fillMaxWidth"),
        )
        self._extension(
            # A genuine `kotlin.Float`, not a value class: the same tag as `Dp` over a different
            # declared type, which is the only machine-checkable form of "this might pack".
            "androidx.compose.ui.draw.zIndex",
            ("zIndex",), ("FLOAT",), ("kotlin.Float",), (False,),
            self._logged("zIndex", lambda a: f"zIndex({_dp(a[0])})"),
        )
        self._extension(
            # A packed value class: raw 16 decodes as `TextUnit.Unspecified`, silently. Nothing
            # binds such a parameter today; the entry exists so the refusal has something to refuse.
            "androidx.compose.foundation.layout.paddingFromBaseline__TextUnit",
            ("top",), ("FLOAT",), (TEXT_UNIT,), (False,),
            self._logged("paddingFromBaseline__TextUnit",
                         lambda a: f"paddingFromBaseline({_dp(a[0])})"),
        )
        self._add(
            # The name the snake -> camel rule cannot invert. Fictional, and placed in a mapped
            # package (`pythonx.compose.ui`) so the re-export rule is what reaches it.
            "androidx.compose.ui.toURLString", 1, ("raw",), ("STRING",), ("kotlin.String",),
            "STRING", "kotlin.String", False, None, (False,),
            lambda args: "url:" + args[0],
        )
        for layout_composable in ("Column", "Row", "Spacer"):
            # Shape only: the notebook imports these from material3 and Kotlin declares them in
            # foundation.layout. Nothing here composes; the tests check which object a name reaches.
            self._add(
                f"androidx.compose.foundation.layout.{layout_composable}", 1, ("modifier",),
                ("OBJECT",), (MODIFIER,), "UNIT", "kotlin.Unit", False, None, (True,),
                lambda args: None,
            )
        # Object constants, the way `ArtifactScanner.constantsOf` binds them: a `STATIC_GETTER` with no
        # parameters, named `<package>.<Object>.<Constant>`, returning the constant's declared type.
        for constant, declared in (
            ("End", ARRANGEMENT_HORIZONTAL), ("Start", ARRANGEMENT_HORIZONTAL),
            ("Top", ARRANGEMENT_VERTICAL), ("SpaceBetween", ARRANGEMENT_BOTH),
        ):
            self._constant(f"{ARRANGEMENT}.{constant}", declared)
        for constant, declared in (
            ("End", ALIGNMENT_HORIZONTAL), ("CenterHorizontally", ALIGNMENT_HORIZONTAL),
            ("Top", ALIGNMENT_VERTICAL), ("Center", ALIGNMENT),
        ):
            self._constant(f"{ALIGNMENT}.{constant}", declared)
        self._add(
            # A function inside an object: reached through the object, camelCase in Kotlin.
            f"{ARRANGEMENT}.spacedBy", 1, ("space",), ("FLOAT",), (DP,),
            "OBJECT", ARRANGEMENT_BOTH, False, None, (False,),
            lambda args: StubConstant(f"spacedBy({_dp(args[0])})"),
        )

        # Icons, shaped after python-multiplatform #37/#38 as the ecosystem reports them: `Icons.Default`
        # is a `STATIC_GETTER` of the object `Icons` whose declared type is `Icons.Filled` (the
        # property's type, not `Default`'s own), and `Icons.Default.Add` is the top-level extension
        # property `AddKt.getAdd(Icons$Filled)` -- a `GETTER` named by its package and property, read on
        # `Icons.Filled`, whose receiver is `args[0]` and not a slot, returning an `ImageVector`.
        self._add(
            f"{ICONS}.Default", 0, (), (), (), "OBJECT", ICONS_FILLED, False, None, (),
            lambda args: self.filled, kind="STATIC_GETTER",
        )
        for icon in ("Add", "Edit"):
            self._add(
                f"{ICONS_PACKAGE}.filled.{icon}", 0, (), (), (), "OBJECT", IMAGE_VECTOR, False,
                ICONS_FILLED, (),
                lambda args, icon=icon: self._read_icon(icon), kind="GETTER",
            )
        self._add(
            # A generic function: `T` is unbounded, so its slot is declared `kotlin.Any`.
            f"{RUNTIME}.mutableStateOf", 1, ("value",), ("OBJECT",), (KOTLIN_ANY,),
            "OBJECT", MUTABLE_STATE, False, None, (False,),
            lambda args: StubState(args[0]),
        )
        self._add(
            f"{MUTABLE_STATE}.value", 0, (), (), (), "OBJECT", KOTLIN_ANY, False, MUTABLE_STATE, (),
            lambda args: args[0].value, kind="GETTER",
        )
        self._add(
            f"{MUTABLE_STATE}.value=", 1, ("value",), ("OBJECT",), (KOTLIN_ANY,),
            "UNIT", "kotlin.Unit", False, MUTABLE_STATE, (False,),
            lambda args: args[0].write(args[1]), kind="SETTER",
        )

    def _composable(self, name, params, body, returns=None):
        """A `@Composable` row: `params` are (name, tag, type, has_default), then the synthetic slots.

        `$composer`, `$changed` and `$default` close the row the way the Compose compiler spells
        them; `PythonxAdapter` recognises a composable by `$composer` alone and fills the three.
        """
        names = tuple(p[0] for p in params) + ("$composer", "$changed", "$default")
        tags = tuple(p[1] for p in params) + ("OBJECT", "INT", "INT")
        types = tuple(p[2] for p in params) + ("androidx.compose.runtime.Composer", "kotlin.Int", "kotlin.Int")
        defaults = tuple(p[3] for p in params) + (False, False, False)
        label = name.rpartition(".")[2]

        def run(args):
            self.composable_calls.append(label)
            return body(args)

        return_tag, return_type = ("UNIT", "kotlin.Unit") if returns is None else ("OBJECT", returns)
        self._add(name, len(names), names, tags, types, return_tag, return_type, False, None,
                  defaults, run)

    def _build_text_field(self):
        text_args = (("initialText", "STRING", "kotlin.String", True),
                     ("initialSelection", "OBJECT", TEXT_RANGE, True))
        self._add(
            f"{TEXT_FIELD_STATE}__String_TextRange", 2, ("initialText", "initialSelection"),
            ("STRING", "OBJECT"), ("kotlin.String", TEXT_RANGE), "OBJECT", TEXT_FIELD_STATE,
            False, None, (True, True),
            lambda args: StubTextFieldState("" if args[0] is None else args[0]),
        )
        self._composable(
            f"{TEXT_INPUT}.rememberTextFieldState", text_args,
            lambda args: StubTextFieldState("" if args[0] is None else args[0]), TEXT_FIELD_STATE,
        )
        self._add(
            f"{TEXT_FIELD_STATE}.text", 0, (), (), (), "STRING", "kotlin.CharSequence", False,
            TEXT_FIELD_STATE, (), lambda args: args[0].text, kind="GETTER",
        )

        def write(label, effect):
            def body(args):
                self.calls.append(label)
                effect(args)

            return body

        def place_at_end(args):
            args[0].text = args[1]

        def clear(args):
            args[0].text = ""

        for leaf, names, tags, types, effect in (
            ("setTextAndPlaceCursorAtEnd", ("<receiver>", "text"), ("OBJECT", "STRING"),
             (TEXT_FIELD_STATE, "kotlin.String"), place_at_end),
            ("clearText", ("<receiver>",), ("OBJECT",), (TEXT_FIELD_STATE,), clear),
        ):
            self._add(
                f"{TEXT_INPUT}.{leaf}", len(names), names, tags, types, "UNIT", "kotlin.Unit", True,
                TEXT_FIELD_STATE, (False,) * len(names), write(leaf, effect),
            )

        def remember_flags(args):
            self.last_text_field_flags = {"readOnly": args[3], "isError": args[4]}
            self.last_text_field_modifier = None if args[1] is None else args[1].describe()

        self._composable(
            f"{MATERIAL3}.TextField__TextFieldState",
            (("state", "OBJECT", TEXT_FIELD_STATE, False), ("modifier", "OBJECT", MODIFIER, True),
             ("enabled", "BOOLEAN", "kotlin.Boolean", True),
             ("readOnly", "BOOLEAN", "kotlin.Boolean", True),
             ("isError", "BOOLEAN", "kotlin.Boolean", True)),
            remember_flags,
        )
        self._composable(
            f"{MATERIAL3}.TextField__String",
            (("value", "STRING", "kotlin.String", False), ("modifier", "OBJECT", MODIFIER, True)),
            lambda args: None,
        )

    def _read_icon(self, icon):
        self.calls.append(f"Icons.Filled.{icon}")
        return StubConstant(icon)

    def _scalar_boxes(self):
        """`PythonCallables`' box entries, the shape python-multiplatform 26485a02 (#69) registers.

        `PythonxAdapter._box_scalar` turns a Python scalar bound for a `kotlin.Any` slot into the
        handle of a Kotlin box by calling one of these; `unboxScalar` turns a handle read back out of
        such a slot into the scalar again, releasing it, or answers None for any other object.
        Names and fields are those of `PythonCallables.kt` (`boxEntry`, `UNBOX_SCALAR`).
        """
        prefix = "python.multiplatform.ffi.pythonx.PythonCallables."
        for leaf, tag, type_name in (
            ("boxInt", "INT", "kotlin.Int"), ("boxLong", "INT", "kotlin.Long"),
            ("boxDouble", "FLOAT", "kotlin.Double"), ("boxBoolean", "BOOLEAN", "kotlin.Boolean"),
            ("boxString", "STRING", "kotlin.String"),
        ):
            self._add(prefix + leaf, 1, ("value",), (tag,), (type_name,), "INT", None, False, None,
                      (False,), lambda args: self._handle(args[0]))
        self._add(prefix + "unboxScalar", 1, ("handle",), ("INT",), ("kotlin.Long",), "OBJECT", None,
                  False, None, (False,), self._unbox)

    def _unbox(self, args):
        held = self._handles.get(args[0])
        if not isinstance(held, (bool, int, float, str)):
            return None
        self.release(args[0])
        return held

    def _build_saveable(self):
        """`rememberSaveableWrapper(initial)`, shaped after python-multiplatform #174 (`8c56f19b`).

        A `@Composable` in python-multiplatform-compose (`RememberSaveable.kt`) that wraps the state
        matching the boxed value's Kotlin type in `rememberSaveable { ... }`, and refuses any other
        type. Here it logs `initial` and returns a fresh state; the type dispatch, and that Compose
        keeps the state across recomposition, rotation and process restart, are
        python-multiplatform's proof (`RememberSaveableRenderTest`), not this fixture's.
        """

        def remember(args):
            self.saveable_calls.append(args[0])
            return StubState(args[0])

        self._composable(
            f"{COMPOSE_HOST}.rememberSaveableWrapper",
            (("initial", "OBJECT", KOTLIN_ANY, False),),
            remember, MUTABLE_STATE,
        )

    def _build_color(self):
        """`Color`: a Kotlin object whose name is also a function in its package (python-multiplatform #78).

        The binder makes such a module callable (`_make_callable`): `Color(0xFFFFFFFF)` calls the
        function, `Color.Red` reads a constant of the object. One overload is modelled; the real
        `Color(Int)` / `Color(Long)` pair and its ambiguity are python-multiplatform #146.
        """
        self._add(
            COLOR, 1, ("color",), ("INT",), ("kotlin.Long",), "OBJECT", COLOR, False, None,
            (False,), lambda args: StubConstant(f"Color({args[0]:#x})"),
        )
        self._constant(f"{COLOR}.Red", COLOR)

    def _constant(self, name, declared):
        self._add(name, 0, (), (), (), "OBJECT", declared, False, None, (),
                  lambda args, label=name.rpartition(".")[2]: StubConstant(label), kind="STATIC_GETTER")
