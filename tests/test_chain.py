"""The chain, the dispatcher and the naming rule, as an application reaches them: through `pythonx`.

The binder serves Kotlin names (`androidx.compose.foundation.layout.paddingValuesOf`) and renames
nothing. These tests go through this package's own modules (`pythonx.compose.*`), so what they
check is the re-export rule in `pythonx/compose/_reexport.py` on top of the binder's real Python,
read out of a `PythonMultiplatform` checkout by `tests/adapter.py`.

    python3 -m pytest tests -q

Requires a `PythonMultiplatform` checkout beside this one, or `PYTHONMULTIPLATFORM_HOME`.
"""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402


class AdapterCase(unittest.TestCase):
    """One binding layer and one host per test, because a table install is destructive."""

    def setUp(self):
        try:
            self.binding = adapter_loader.install()
        except adapter_loader.AdapterUnavailable as unavailable:
            self.skipTest(str(unavailable))
        self.host = fake_host.FakeHost()
        self.host.bind()
        self.host.register(self.binding)
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
        self.binding.register_empty(fake_host.MODIFIER, fake_host.EMPTY_MODIFIER)
        return self.modifier_type()

    def empty(self):
        return self.register_empty().empty()

    def describe(self, modifier):
        import pythonx.compose.ui as ui

        return ui.describe_modifier(modifier)

    def needs_member_resolver(self):
        """Receiver methods by snake_case name need the binder's member-resolver hook.

        python-multiplatform #17 adds it; until a checkout has it, these tests skip rather than pass.
        """
        if not hasattr(self.binding, "add_member_resolver"):
            self.skipTest("the binder has no add_member_resolver yet (python-multiplatform #17)")


class TheBinderSourcesAreReadable(AdapterCase):

    def test_both_sources_came_out_of_the_kotlin_literals_and_compile(self):
        binding = adapter_loader.read_adapter_source()
        surface = adapter_loader.read_surface_source()
        self.assertIn("class _Finder", binding)
        self.assertIn("KOTLIN_DEFAULT", surface)
        compile(binding, "python_multiplatform/binding.py", "exec")
        compile(surface, "python_multiplatform/__init__.py", "exec")

    def test_the_binder_renames_nothing(self):
        """The rule lives here; the binder has no snake_case of its own to lean on."""
        source = adapter_loader.read_adapter_source()
        self.assertNotIn("def to_python_name(", source)
        self.assertNotIn("def register_package(", source)

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

    def test_modifier_is_the_binders_proxy_class(self):
        import androidx.compose.ui as kotlin_ui

        self.assertIs(kotlin_ui.Modifier, self.modifier_type())

    def test_chain_from_the_class_object(self):
        chained = self.register_empty().padding(16).size(24)
        self.assertEqual("padding(16.0) -> size(24.0)", self.describe(chained))
        self.assertEqual(["padding__Dp", "size__Dp"], self.host.calls)

    def test_chain_from_an_instance(self):
        self.needs_member_resolver()
        chained = self.empty().padding(16).size(24).fill_max_width()
        self.assertEqual(
            "padding(16.0) -> size(24.0) -> fillMaxWidth", self.describe(chained)
        )

    def test_a_resolved_snake_case_method_leaves_the_binders_class_kotlin_named(self):
        """The alias lives in the binder's resolver registry, not on its proxy class."""
        self.needs_member_resolver()
        modifier = self.empty().fill_max_width()
        self.assertEqual("fillMaxWidth", self.describe(modifier))
        self.assertNotIn("fill_max_width", vars(type(modifier)))
        self.assertNotIn("fill_max_width", dir(type(modifier)))

    def test_each_link_is_a_new_receiver_not_a_mutation(self):
        base = self.empty().padding(8)
        left = base.size(1)
        right = base.size(2)
        self.assertEqual("padding(8.0)", self.describe(base))
        self.assertEqual("padding(8.0) -> size(1.0)", self.describe(left))
        self.assertEqual("padding(8.0) -> size(2.0)", self.describe(right))

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

    def test_the_module_function_dispatches_with_snake_case_keywords(self):
        import pythonx.compose.foundation.layout as layout

        values = layout.padding_values_of(8)
        result = layout.padding(self.empty(), padding_values=values)
        self.assertEqual(["padding__PaddingValues"], self.host.calls)
        self.assertEqual("padding(pv(8.0))", self.describe(result))


class MethodKeywords(AdapterCase):
    """SPEC S4.1: a method's keywords are snake_case like a module function's.

    The member resolver answers `(kotlin_name, {python_keyword: kotlinParameter})`, built from
    `python_multiplatform.describe_member(type, member)` (python-multiplatform #54).
    """

    def setUp(self):
        super().setUp()
        import python_multiplatform

        self.needs_member_resolver()
        if not hasattr(python_multiplatform, "describe_member"):
            self.skipTest("the binder has no describe_member(type, member) yet (python-multiplatform #54)")

    def values(self):
        import pythonx.compose.foundation.layout as layout

        return layout.padding_values_of(8)

    def test_a_snake_case_keyword_reaches_the_kotlin_parameter_of_the_overload(self):
        result = self.empty().padding(padding_values=self.values())
        self.assertEqual(["padding__PaddingValues"], self.host.calls)
        self.assertEqual("padding(pv(8.0))", self.describe(result))

    def test_keywords_that_are_already_one_word_are_unchanged(self):
        result = self.empty().padding(horizontal=8, vertical=4)
        self.assertEqual(["padding__Dp_Dp"], self.host.calls)
        self.assertEqual("padding(h=8.0, v=4.0)", self.describe(result))

    def test_the_kotlin_spelling_still_works_at_run_time(self):
        self.empty().padding(paddingValues=self.values())
        self.assertEqual(["padding__PaddingValues"], self.host.calls)

    def test_a_snake_case_method_takes_snake_case_keywords(self):
        """The name is resolved (`z_index`) and the keyword is mapped on it too (`z_index=`)."""
        result = self.empty().z_index(z_index=1.5)
        self.assertEqual("zIndex(1.5)", self.describe(result))
        self.assertEqual(["zIndex"], self.host.calls)

    def test_an_unknown_keyword_still_reaches_the_binders_refusal_with_its_candidates(self):
        with self.assertRaises(TypeError) as raised:
            self.empty().padding(padding_valuez=1)
        message = str(raised.exception)
        self.assertIn("Candidates", message)
        self.assertIn("padding__PaddingValues", message)

    def test_the_map_is_metadata_and_is_asked_for_once_per_member(self):
        import python_multiplatform

        original, asked = python_multiplatform.describe_member, []

        def counting(*args):
            asked.append(args)
            return original(*args)

        python_multiplatform.describe_member = counting
        self.addCleanup(setattr, python_multiplatform, "describe_member", original)
        modifier = self.empty()
        modifier.padding(padding_values=self.values())
        modifier.padding(padding_values=self.values())
        self.assertEqual([(fake_host.MODIFIER, "padding")], asked)

    def test_the_map_lists_every_overloads_parameters_and_not_the_receiver(self):
        from pythonx.compose._reexport import member_name

        answer = member_name(fake_host.MODIFIER, "padding", ["padding"])
        self.assertEqual("padding", answer[0])
        self.assertEqual("paddingValues", answer[1]["padding_values"])
        self.assertNotIn("receiver", answer[1])
        self.assertNotIn("horizontal", answer[1])  # one word: Kotlin's spelling is the same


class MethodKeywordsNeedTheBindersDescription(AdapterCase):
    """Without `describe_member` a method's keywords are Kotlin's and its names still resolve."""

    def setUp(self):
        super().setUp()
        import python_multiplatform

        self.needs_member_resolver()
        original = getattr(python_multiplatform, "describe_member", None)
        if original is not None:
            del python_multiplatform.describe_member
            self.addCleanup(setattr, python_multiplatform, "describe_member", original)

    def test_the_name_resolves_and_kotlin_keywords_work(self):
        import pythonx.compose.foundation.layout as layout

        modifier = self.empty().fill_max_width()
        self.assertEqual("fillMaxWidth", self.describe(modifier))
        self.empty().padding(paddingValues=layout.padding_values_of(8))
        self.assertEqual("padding__PaddingValues", self.host.calls[-1])

    def test_a_snake_case_keyword_is_the_binders_refusal(self):
        import pythonx.compose.foundation.layout as layout

        with self.assertRaises(TypeError):
            self.empty().padding(padding_values=layout.padding_values_of(8))


class Names(AdapterCase):
    """PascalCase for types, snake_case for everything else, forward by rule and never inverted."""

    def test_camel_case_becomes_snake_case(self):
        from pythonx.compose._reexport import python_name

        self.assertEqual("fill_max_width", python_name("fillMaxWidth"))
        self.assertEqual("z_index", python_name("zIndex"))
        self.assertEqual("to_url_string", python_name("toURLString"))
        self.assertEqual("padding__Dp_Dp", python_name("padding__Dp_Dp"))

    def test_a_type_name_is_left_alone(self):
        from pythonx.compose._reexport import python_name

        self.assertEqual("Modifier", python_name("Modifier"))

    def test_a_name_the_reverse_rule_cannot_invert_still_resolves(self):
        import pythonx.compose.ui as ui

        self.assertEqual("url:x", ui.to_url_string("x"))

    def test_the_kotlin_camel_case_spelling_is_not_a_second_name(self):
        import pythonx.compose.foundation.layout as layout

        with self.assertRaises(AttributeError):
            layout.paddingValuesOf  # noqa: B018

    def test_on_click_not_onclick(self):
        """`UI.ipynb` writes `onclick`; the decision on record is that `pythonx` is the reference."""
        from pythonx.compose._reexport import python_name

        self.assertEqual("on_click", python_name("onClick"))

    def test_the_signature_carries_snake_case_parameter_names(self):
        import pythonx.compose.foundation.layout as layout

        parameters = list(inspect.signature(layout.padding__PaddingValues).parameters)
        self.assertEqual(["receiver", "padding_values"], parameters)

    def test_a_defaulted_parameter_keeps_the_kotlin_default_marker(self):
        import python_multiplatform
        import pythonx.compose.foundation.layout as layout

        signature = inspect.signature(layout.padding__Dp_Dp)
        self.assertIs(python_multiplatform.KOTLIN_DEFAULT, signature.parameters["horizontal"].default)

    def test_an_unknown_keyword_reaches_the_binders_refusal(self):
        import pythonx.compose.foundation.layout as layout

        with self.assertRaises(TypeError) as raised:
            layout.padding_values_of(everything=8)
        self.assertIn("everything", str(raised.exception))


class ValueClasses(AdapterCase):
    """`Dp` takes a raw number, a packed wrapper must not; the manifest says which."""

    def test_a_raw_number_reaches_a_dp_parameter(self):
        self.assertEqual("padding(16.0)", self.describe(self.empty().padding(16)))

    def test_the_manifest_allowlist_is_what_lets_a_number_through(self):
        """The binder alone refuses a raw number for `Dp`; importing through `pythonx` allows it."""
        import androidx.compose.foundation.layout as kotlin_layout

        with self.assertRaises(TypeError):
            kotlin_layout.paddingValuesOf(8)
        import pythonx.compose.foundation.layout as layout

        result = self.empty().padding(layout.padding_values_of(8))
        self.assertEqual("padding(pv(8.0))", self.describe(result))

    def test_a_dp_proxy_reaches_the_same_parameter(self):
        result = self.empty().padding(self.binding.value_of(fake_host.DP, 16))
        self.assertEqual("padding(16.0)", self.describe(result))

    def test_a_plain_float_parameter_is_not_treated_as_a_value_class(self):
        self.needs_member_resolver()
        self.assertEqual("zIndex(1.5)", self.describe(self.empty().z_index(1.5)))

    def test_a_packed_value_class_refuses_a_raw_number_and_says_why(self):
        self.needs_member_resolver()
        with self.assertRaises(TypeError) as raised:
            self.empty().padding_from_baseline(16)
        message = str(raised.exception)
        self.assertIn("TextUnit", message)
        self.assertIn("reinterpreted", message)

    def test_the_allowlist_can_be_extended_at_run_time(self):
        self.needs_member_resolver()
        self.binding.allow_raw_primitive(fake_host.TEXT_UNIT)
        self.assertEqual(
            "paddingFromBaseline(16.0)", self.describe(self.empty().padding_from_baseline(16))
        )


class Laziness(AdapterCase):
    """A mapped module is a file on disk; the names inside it resolve on first use."""

    def test_a_mapped_package_is_importable(self):
        import pythonx.compose.foundation.layout as layout

        self.assertEqual("pythonx.compose.foundation.layout", layout.__name__)

    def test_a_package_with_no_file_is_not(self):
        with self.assertRaises(ModuleNotFoundError):
            import pythonx.compose.nothing.here  # noqa: F401

    def test_a_name_is_adapted_once_and_then_lives_in_the_module_dict(self):
        import pythonx.compose.foundation.layout as layout

        self.assertNotIn("padding", vars(layout))
        first = layout.padding
        self.assertIn("padding", vars(layout))
        self.assertIs(first, layout.padding)

    def test_dir_reports_what_is_bound_under_pythonic_names(self):
        import pythonx.compose.foundation.layout as layout

        names = dir(layout)
        self.assertIn("padding", names)
        self.assertIn("size", names)
        self.assertIn("fill_max_width", names)
        self.assertNotIn("fillMaxWidth", names)

    def test_without_the_binding_layer_a_name_says_what_is_missing(self):
        import pythonx.compose.foundation.layout as layout

        adapter_loader.uninstall()
        import pythonx.compose.foundation.layout as fresh

        self.assertIsNot(layout, fresh)
        with self.assertRaises(RuntimeError) as raised:
            fresh.padding  # noqa: B018
        self.assertIn("PythonxAdapter.install()", str(raised.exception))


class ObjectNamespaces(AdapterCase):
    """`Arrangement`, `Alignment`: a Kotlin object is a namespace, read by the same rule."""

    def label_of(self, proxy):
        return self.host._object(proxy._pm_handle).label

    def test_a_constant_is_reached_through_the_pythonx_module(self):
        import pythonx.compose.layout as layout

        self.assertEqual("End", self.label_of(layout.Arrangement.End))

    def test_the_same_object_from_its_kotlin_home_and_the_short_spelling(self):
        import pythonx.compose.foundation.layout as long
        import pythonx.compose.layout as short

        self.assertEqual("Start", self.label_of(long.Arrangement.Start))
        self.assertEqual("Start", self.label_of(short.Arrangement.Start))

    def test_a_constant_is_read_again_each_time_not_frozen(self):
        import pythonx.compose.ui as ui

        first, second = ui.Alignment.Center, ui.Alignment.Center
        self.assertIsNot(first, second)
        self.assertEqual("Center", self.label_of(second))

    def test_a_function_inside_an_object_is_snake_case(self):
        import pythonx.compose.layout as layout

        self.assertEqual("spacedBy(8.0)", self.label_of(layout.Arrangement.spaced_by(8)))
        with self.assertRaises(AttributeError):
            layout.Arrangement.spacedBy  # noqa: B018

    def test_dir_of_the_namespace_reports_pythonic_names(self):
        import pythonx.compose.layout as layout

        names = dir(layout.Arrangement)
        self.assertIn("SpaceBetween", names)
        self.assertIn("spaced_by", names)
        self.assertNotIn("spacedBy", names)

    def test_an_unknown_constant_says_where_it_looked(self):
        import pythonx.compose.ui as ui

        with self.assertRaises(AttributeError) as raised:
            ui.Alignment.Nowhere  # noqa: B018
        self.assertIn("androidx.compose.ui.Alignment", str(raised.exception))


class GroupedObjectConstants(AdapterCase):
    """INTENT 5.3, SPEC S7.1: `Alignment.Horizontal.End` beside Kotlin's flat `Alignment.End`.

    A group is the constants of an object whose declared type is one type nested in it, read with
    `python_multiplatform.describe(module, name)` -- never by reading a constant.
    """

    def setUp(self):
        super().setUp()
        import python_multiplatform

        if len(inspect.signature(python_multiplatform.describe).parameters) < 2:
            self.skipTest("the binder has no describe(module, name) yet (python-multiplatform #36)")

    def label_of(self, proxy):
        return self.host._object(proxy._pm_handle).label

    def test_the_grouped_spelling_reads_the_constant(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        self.assertEqual("End", self.label_of(ui.Alignment.Horizontal.End))
        self.assertEqual("Top", self.label_of(ui.Alignment.Vertical.Top))
        self.assertEqual("Start", self.label_of(layout.Arrangement.Horizontal.Start))
        self.assertEqual("SpaceBetween", self.label_of(layout.Arrangement.HorizontalOrVertical.SpaceBetween))

    def test_both_spellings_are_the_same_live_read(self):
        import pythonx.compose.ui as ui

        flat, grouped, again = ui.Alignment.End, ui.Alignment.Horizontal.End, ui.Alignment.Horizontal.End
        self.assertEqual(self.label_of(flat), self.label_of(grouped))
        self.assertIsNot(grouped, again)  # read again on every access, like the flat spelling
        self.assertIs(type(flat), type(grouped))

    def test_a_group_holds_exactly_the_constants_of_its_declared_type(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        self.assertEqual(["CenterHorizontally", "End"], dir(ui.Alignment.Horizontal))
        self.assertEqual(["Top"], dir(ui.Alignment.Vertical))
        self.assertEqual(["End", "Start"], dir(layout.Arrangement.Horizontal))
        self.assertEqual(["Top"], dir(layout.Arrangement.Vertical))
        self.assertEqual(["SpaceBetween"], dir(layout.Arrangement.HorizontalOrVertical))

    def test_a_constant_declared_as_a_supertype_is_in_no_narrower_group(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        self.assertIn("End", dir(ui.Alignment.Horizontal))
        self.assertIn("SpaceBetween", dir(layout.Arrangement.HorizontalOrVertical))
        with self.assertRaises(AttributeError):
            ui.Alignment.Horizontal.Center  # noqa: B018  -- declared `Alignment`
        with self.assertRaises(AttributeError):
            layout.Arrangement.Horizontal.SpaceBetween  # noqa: B018  -- declared `HorizontalOrVertical`

    def test_a_name_the_group_does_not_hold_names_the_groups_kotlin_type(self):
        import pythonx.compose.ui as ui

        with self.assertRaises(AttributeError) as raised:
            ui.Alignment.Horizontal.Top  # noqa: B018  -- `Top` is an `Alignment.Vertical`
        self.assertIn("androidx.compose.ui.Alignment.Horizontal", str(raised.exception))
        self.assertIn("'Top'", str(raised.exception))

    def test_a_name_that_is_no_nested_type_is_still_unknown(self):
        import pythonx.compose.ui as ui

        self.assertIn("Horizontal", dir(ui.Alignment))
        with self.assertRaises(AttributeError):
            ui.Alignment.Diagonal  # noqa: B018

    def test_dir_of_the_object_lists_its_groups(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        self.assertTrue({"Horizontal", "Vertical", "End", "Center"} <= set(dir(ui.Alignment)))
        self.assertTrue({"Horizontal", "Vertical", "HorizontalOrVertical"} <= set(dir(layout.Arrangement)))

    def test_classifying_reads_no_constant(self):
        import pythonx.compose.ui as ui

        before = self.host._next_handle
        dir(ui.Alignment)
        ui.Alignment.Horizontal  # noqa: B018
        self.assertEqual(before, self.host._next_handle, "a constant's getter ran to classify it")

    def test_the_classification_is_computed_once_per_object(self):
        import python_multiplatform
        import pythonx.compose.ui as ui

        original, asked = python_multiplatform.describe, []

        def counting(*args):
            asked.append(args)
            return original(*args)

        python_multiplatform.describe = counting
        self.addCleanup(setattr, python_multiplatform, "describe", original)
        ui.Alignment.Horizontal  # noqa: B018
        first = len(asked)
        ui.Alignment.Vertical  # noqa: B018
        dir(ui.Alignment)
        self.assertGreater(first, 0)
        self.assertEqual(first, len(asked))

    def test_a_kotlin_member_wins_over_a_group(self):
        # A fictional constant of `Arrangement` named like one of its nested types.
        self.host._constant(f"{fake_host.ARRANGEMENT}.Vertical", fake_host.ARRANGEMENT_VERTICAL)
        self.host.register(self.binding)
        import pythonx.compose.layout as layout

        self.assertEqual("Vertical", self.label_of(layout.Arrangement.Vertical))
        self.assertEqual(["End", "Start"], dir(layout.Arrangement.Horizontal))

    def test_a_group_is_read_only(self):
        import pythonx.compose.ui as ui

        group = ui.Alignment.Horizontal
        with self.assertRaises(AttributeError):
            group.End = None
        self.assertEqual("End", self.label_of(group.End))

    def test_without_describe_by_name_there_are_no_groups_and_the_flat_spelling_stays(self):
        import python_multiplatform
        import pythonx.compose.ui as ui

        original = python_multiplatform.describe
        python_multiplatform.describe = lambda fn: original(fn)  # the one-argument binder
        self.addCleanup(setattr, python_multiplatform, "describe", original)
        self.assertEqual("End", self.label_of(ui.Alignment.End))
        with self.assertRaises(AttributeError):
            ui.Alignment.Horizontal  # noqa: B018
        self.assertNotIn("Horizontal", dir(ui.Alignment))


class ManifestAliases(AdapterCase):
    """INTENT 5.2: `Column`, `Row`, `Spacer` from `material3`, as the notebook imports them."""

    def test_the_notebook_import_resolves_to_the_layout_object(self):
        from pythonx.compose.layout import Column as from_layout
        from pythonx.compose.material3 import Column, Row, Spacer

        self.assertIs(from_layout, Column)
        self.assertIsNotNone(Row)
        self.assertIsNotNone(Spacer)

    def test_dir_of_material3_lists_the_aliases(self):
        import pythonx.compose.material3 as material3

        for name in ("Column", "Row", "Spacer"):
            self.assertIn(name, dir(material3))

    def test_a_name_not_listed_is_not_borrowed(self):
        import pythonx.compose.material3 as material3

        with self.assertRaises(AttributeError):
            material3.padding_values_of  # noqa: B018


class SubmodulesWithoutABinder(unittest.TestCase):
    """`from pythonx.compose.ui import modifier` reaches the file even when no binder is installed.

    `from package import name` asks the package for the attribute first and only imports a
    submodule if that raises AttributeError. The re-export `__getattr__` raised RuntimeError ("the
    binding layer is not installed") for every name, so the submodule was never tried.
    """

    def setUp(self):
        adapter_loader.uninstall()
        self.addCleanup(adapter_loader.uninstall)
        root = str(Path(__file__).resolve().parents[1])
        if root not in sys.path:
            sys.path.insert(0, root)

    def test_from_import_of_a_submodule_needs_no_binder(self):
        from pythonx.compose.ui import modifier

        self.assertTrue(callable(modifier.install))

    def test_a_kotlin_name_still_says_the_binder_is_missing(self):
        import pythonx.compose.ui as ui

        with self.assertRaises(RuntimeError):
            ui.Modifier  # noqa: B018


class Handles(AdapterCase):
    """The binder's proxy owns a handle; dropping it gives the handle back."""

    def test_dropping_a_proxy_releases_its_handle(self):
        modifier = self.empty().padding(16)
        handle = modifier._pm_handle
        self.assertIn(handle, self.host.live_handles())
        del modifier
        self.assertIn(handle, self.host.released)


if __name__ == "__main__":
    unittest.main()
