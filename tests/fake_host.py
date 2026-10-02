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
ALIGNMENT_HORIZONTAL = ALIGNMENT + ".Horizontal"
ALIGNMENT_VERTICAL = ALIGNMENT + ".Vertical"

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


class StubPaddingValues:
    """An ordinary object parameter, so two arity-2 overloads differ by declared type alone."""

    __slots__ = ("label",)

    def __init__(self, label):
        self.label = label


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
        unpacked = [
            self._object(value) if tags[index] == "OBJECT" else value
            for index, value in enumerate(args)
        ]
        result = body(unpacked)
        if row[7] == "OBJECT":
            return self._handle(result)
        return result

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

    def _constant(self, name, declared):
        self._add(name, 0, (), (), (), "OBJECT", declared, False, None, (),
                  lambda args, label=name.rpartition(".")[2]: StubConstant(label), kind="STATIC_GETTER")
