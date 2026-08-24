"""The chain, and the four things `docs/pythonx-adapter-design.md` asks the adaptation layer for.

This is the test the 2024 tree never had. `pythonx/compose/ui/modifier.py` shipped a `padding()`
that composed nothing and a `fill_max_size()` that returned `self`, and nothing in the repository
could have noticed, because there was nothing to run.

    python3 -m unittest discover -s tests -v

Requires a `PythonMultiplatform` checkout beside this one, or `PYTHONMULTIPLATFORM_HOME`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402


class AdapterCase(unittest.TestCase):
    """One adaptation layer and one host per test, because a table install is destructive."""

    def setUp(self):
        try:
            source = adapter_loader.read_adapter_source()
        except adapter_loader.AdapterUnavailable as unavailable:
            self.skipTest(str(unavailable))
        self.host = fake_host.FakeHost()
        self.host.bind()
        self.pythonx = adapter_loader.install(source)
        self.host.register(self.pythonx)
        self.addCleanup(self.host.unbind)
        self.addCleanup(adapter_loader.uninstall)

    def modifier_type(self):
        """`Modifier` reached the way an application reaches it: by importing the module."""
        import pythonx.compose.ui as ui

        return ui.Modifier

    def register_empty(self):
        """The seam `pythonx/compose/ui/modifier.py` owns, spelled out here rather than imported.

        `test_modifier_module.py` is what tests that file; this keeps the chain tests independent of
        it, so a break in one does not read as a break in the other.
        """
        self.pythonx.register_empty(fake_host.MODIFIER, fake_host.EMPTY_MODIFIER)
        return self.modifier_type()

    def empty(self):
        return self.register_empty().empty()

    def describe(self, modifier):
        import pythonx.compose.ui as ui

        return ui.describe_modifier(modifier)


class TheAdapterSourceIsReadable(AdapterCase):

    def test_the_source_came_out_of_the_kotlin_literal_and_compiles(self):
        source = adapter_loader.read_adapter_source()
        self.assertIn("class _Finder", source)
        self.assertIn("def to_python_name(", source)
        compile(source, "pythonx/__init__.py", "exec")

    def test_the_table_is_the_walked_shape(self):
        """`padding__Dp` here carries every field the real walked entry carries.

        The mirror of `PythonxAdapterTest.shapeMatchesTheWalkedEntries`, on this side of the
        boundary: if the fixture stops matching the walker, this repository's tests stop being about
        anything, and this is where that shows.
        """
        rows = {row[0]: row for row in self.host.rows()}
        padding = rows["androidx.compose.foundation.layout.padding__Dp"]
        self.assertEqual(("<receiver>", "all"), padding[4])
        self.assertEqual((fake_host.MODIFIER, fake_host.DP), padding[6])
        self.assertEqual(fake_host.MODIFIER, padding[8])
        self.assertTrue(padding[9])
        self.assertEqual(fake_host.MODIFIER, padding[10])
        self.assertEqual((False, False), padding[11])
        symmetric = rows["androidx.compose.foundation.layout.padding__Dp_Dp"]
        self.assertEqual(("<receiver>", "horizontal", "vertical"), symmetric[4])
        self.assertEqual((False, True, True), symmetric[11])
        # The bare name of an overload set is not bound: the walker refuses to arbitrate, which is
        # why there is a dispatcher in Python at all.
        self.assertNotIn("androidx.compose.foundation.layout.padding", rows)


class TheChain(AdapterCase):
    """`Modifier.padding(16).size(24)` -- the thing the 2024 tree could not do."""

    def test_chain_from_the_class_object(self):
        chained = self.register_empty().padding(16).size(24)
        self.assertEqual("padding(16.0) -> size(24.0)", self.describe(chained))
        self.assertEqual(["padding__Dp", "size__Dp"], self.host.calls)

    def test_chain_from_an_instance(self):
        chained = self.empty().padding(16).size(24).fill_max_width()
        self.assertEqual(
            "padding(16.0) -> size(24.0) -> fillMaxWidth", self.describe(chained)
        )

    def test_each_link_is_a_new_receiver_not_a_mutation(self):
        base = self.empty().padding(8)
        left = base.size(1)
        right = base.size(2)
        self.assertEqual("padding(8.0)", self.describe(base))
        self.assertEqual("padding(8.0) -> size(1.0)", self.describe(left))
        self.assertEqual("padding(8.0) -> size(2.0)", self.describe(right))

    def test_a_method_is_attached_to_the_type_once(self):
        first = self.register_empty()
        self.assertNotIn("padding", vars(first))
        first.padding(1)
        self.assertIn("padding", vars(first))
        self.assertIs(first, self.modifier_type())

    def test_an_unbound_name_is_an_attribute_error_that_says_where_it_looked(self):
        with self.assertRaises(AttributeError) as raised:
            self.empty().fill_max_size()
        self.assertIn("fill_max_size", str(raised.exception))
        self.assertIn(fake_host.MODIFIER, str(raised.exception))

    def test_the_class_object_spelling_needs_an_empty_factory_and_says_so(self):
        """Against real Compose this is the state the chain is actually in.

        The walker binds functions; `Modifier` as an expression is `Modifier.Companion`, an object.
        So no name for the empty modifier is bound, and the refusal has to name the seam rather than
        guess. `register_empty` is that seam and it is not registered here.
        """
        with self.assertRaises(TypeError) as raised:
            self.modifier_type().padding(16)
        self.assertIn("register_empty", str(raised.exception))


class OverloadDispatch(AdapterCase):
    """`docs/kotlin-extensions-in-python.md` §3.1: the walker distinguishes, Python decides."""

    def test_selected_by_keyword_name(self):
        result = self.empty().padding(horizontal=8, vertical=4)
        self.assertEqual(["padding__Dp_Dp"], self.host.calls)
        self.assertEqual("padding(h=8.0, v=4.0)", self.describe(result))

    def test_selected_by_argument_count(self):
        self.empty().padding(1, 2, 3, 4)
        self.assertEqual(["padding__Dp_Dp_Dp_Dp"], self.host.calls)

    def test_selected_by_declared_type(self):
        import pythonx.compose.foundation.layout as layout

        values = layout.padding_values_of(8)
        result = self.empty().padding(values)
        self.assertEqual(["padding__PaddingValues"], self.host.calls)
        self.assertEqual("padding(pv(8.0))", self.describe(result))

    def test_a_single_argument_number_still_reaches_the_one_dp_overload(self):
        self.empty().padding(16)
        self.assertEqual(["padding__Dp"], self.host.calls)

    def test_no_overload_matching_names_the_candidates(self):
        with self.assertRaises(TypeError) as raised:
            self.empty().padding(nonsense=1)
        message = str(raised.exception)
        self.assertIn("Candidates", message)
        self.assertIn("padding__Dp_Dp", message)

    def test_the_explicit_spelling_bypasses_the_dispatcher(self):
        getattr(self.empty(), "padding__Dp")(16)
        self.assertEqual(["padding__Dp"], self.host.calls)


class Names(AdapterCase):
    """§3: PascalCase for types, snake_case for everything else, forward by rule."""

    def test_camel_case_becomes_snake_case(self):
        self.assertEqual("fill_max_width", self.pythonx.to_python_name("fillMaxWidth"))
        self.assertEqual("z_index", self.pythonx.to_python_name("zIndex"))
        self.assertEqual("to_url_string", self.pythonx.to_python_name("toURLString"))

    def test_a_type_name_is_left_alone(self):
        self.assertEqual("Modifier", self.pythonx.to_python_name("Modifier"))

    def test_a_name_the_reverse_rule_cannot_invert_still_resolves(self):
        import pythonx.compose.ui.util as util

        self.assertEqual("url:x", util.to_url_string("x"))
        self.assertEqual("toUrlString", self.pythonx.to_kotlin_name("to_url_string"))

    def test_on_click_not_onclick(self):
        """`UI.ipynb` writes `onclick`; the decision on record is that `pythonx` is the reference."""
        self.assertEqual("on_click", self.pythonx.to_python_name("onClick"))


class ValueClasses(AdapterCase):
    """§4.4: `Dp` takes a raw number, a packed wrapper must not."""

    def test_a_raw_number_reaches_a_dp_parameter(self):
        self.assertEqual("padding(16.0)", self.describe(self.empty().padding(16)))

    def test_a_dp_proxy_reaches_the_same_parameter(self):
        # `pythonx.dp(...)` used to exist, defined in the binder itself -- which meant the language
        # boundary shipped a Compose spelling and any other library's value class needed a core
        # edit to get one. The binder now offers only the general form, and `dp` is a name this
        # package owes on top of it. Written the general way until there is somewhere to put the
        # short one: the disk modules under `pythonx/compose/` are never loaded (the adapter's
        # finder answers those imports), so a hand-written `dp` needs a home this package does not
        # have yet.
        result = self.empty().padding(self.pythonx.value_of("androidx.compose.ui.unit.Dp", 16))
        self.assertEqual("padding(16.0)", self.describe(result))

    def test_a_plain_float_parameter_is_not_treated_as_a_value_class(self):
        self.assertEqual("zIndex(1.5)", self.describe(self.empty().z_index(1.5)))

    def test_a_packed_value_class_refuses_a_raw_number_and_says_why(self):
        with self.assertRaises(TypeError) as raised:
            self.empty().padding_from_baseline(16)
        message = str(raised.exception)
        self.assertIn("TextUnit", message)
        self.assertIn("reinterpreted", message)

    def test_the_allowlist_can_be_extended_at_run_time(self):
        self.pythonx.allow_raw_primitive(fake_host.TEXT_UNIT)
        self.assertEqual(
            "paddingFromBaseline(16.0)", self.describe(self.empty().padding_from_baseline(16))
        )


class Laziness(AdapterCase):
    """§2.3: a finder for the module, a `__getattr__` for the names inside it."""

    def test_a_package_something_is_bound_under_is_importable(self):
        import pythonx.compose.foundation.layout as layout

        self.assertEqual("pythonx.compose.foundation.layout", layout.__name__)

    def test_a_package_nothing_is_bound_under_is_not(self):
        with self.assertRaises(ModuleNotFoundError):
            import pythonx.compose.nothing.here  # noqa: F401

    def test_a_name_is_adapted_once_and_then_lives_in_the_module_dict(self):
        import pythonx.compose.foundation.layout as layout

        self.assertNotIn("padding", vars(layout))
        first = layout.padding
        self.assertIn("padding", vars(layout))
        self.assertIs(first, layout.padding)

    def test_dir_reports_what_is_bound(self):
        import pythonx.compose.foundation.layout as layout

        names = dir(layout)
        self.assertIn("padding", names)
        self.assertIn("size", names)
        self.assertIn("fill_max_width", names)


class Handles(AdapterCase):
    """§4.1's proxy is what owns a handle; `kotlin-extensions` §3.2 recorded three leaking."""

    def test_dropping_a_proxy_releases_its_handle(self):
        modifier = self.empty().padding(16)
        handle = modifier._pm_handle
        self.assertIn(handle, self.host.live_handles())
        del modifier
        self.assertIn(handle, self.host.released)


if __name__ == "__main__":
    unittest.main()
