"""`TextField(state=...)`: the state-based overload, and the module that makes its state (issue #10).

Compose owns the text buffer and the IME composing region, so nothing crosses into Python per
keystroke; Python creates a `TextFieldState` and reads or writes it on demand. There is no
per-widget wrapper: `TextField` is androidx's, re-exported by rule, and
`pythonx.compose.foundation.text.input` is the manifest row that reaches `TextFieldState` and
`rememberTextFieldState`.

These tests go through `pythonx.compose.*` against the fake host's rows (`tests/fake_host.py`
says what they are shaped after). What they prove is the Python half: the module resolves, a
constructor and a composable are called with the right slots, a property is read as `str`, an
extension is a snake_case method, and the `state=` keyword selects the state overload. They do not
prove that Compose accepts a composing sequence with no Python callback -- that is
python-multiplatform's render test (E2E #26), judged over up to four frames.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_chain import AdapterCase  # noqa: E402


class TextFieldCase(AdapterCase):

    def setUp(self):
        super().setUp()
        self.needs_member_resolver()
        if not hasattr(self.binding, "push_composer"):
            self.skipTest("the binder has no @Composable binding (push_composer); python-multiplatform #73 shapes need it")
        # Composable rows read the composer `push_composer` was given; a handle stands in for it.
        self.binding.push_composer(self.host.composer())
        self.addCleanup(self.binding.pop_composer)
        from pythonx.compose.foundation.text import input as text_input
        from pythonx.compose import material3

        self.text_input, self.material3 = text_input, material3


class TheTextFieldState(TextFieldCase):

    def test_a_state_made_outside_composition_reads_its_text_as_a_str(self):
        field = self.text_input.TextFieldState("hi")
        self.assertEqual("hi", field.text)
        self.assertIsInstance(field.text, str)

    def test_the_initial_text_is_optional(self):
        self.assertEqual("", self.text_input.TextFieldState().text)

    def test_set_text_and_place_cursor_at_end_writes_it(self):
        field = self.text_input.TextFieldState("hi")
        field.set_text_and_place_cursor_at_end("hello")
        self.assertEqual("hello", field.text)
        self.assertIn("setTextAndPlaceCursorAtEnd", self.host.calls)

    def test_clear_text_empties_it(self):
        field = self.text_input.TextFieldState("hi")
        field.clear_text()
        self.assertEqual("", field.text)

    def test_remember_text_field_state_is_the_composable_that_makes_one(self):
        field = self.text_input.remember_text_field_state("draft")
        self.assertEqual("draft", field.text)
        self.assertEqual(["rememberTextFieldState"], self.host.composable_calls)

    def test_remember_text_field_state_needs_a_composition(self):
        self.binding.pop_composer()
        self.addCleanup(lambda: self.binding.push_composer(self.host.composer()))
        with self.assertRaises(RuntimeError):
            self.text_input.remember_text_field_state("")

    def test_the_kotlin_spelling_works_too(self):
        field = self.text_input.TextFieldState(initialText="kt")
        self.assertEqual("kt", field.text)


class TheStateOverload(TextFieldCase):

    def test_state_selects_the_state_overload(self):
        field = self.text_input.TextFieldState("hi")
        self.material3.TextField(state=field)
        self.assertEqual(["TextField__TextFieldState"], self.host.composable_calls)

    def test_keywords_are_snake_case_and_reach_the_row(self):
        field = self.text_input.TextFieldState("hi")
        self.material3.TextField(state=field, read_only=True, is_error=True)
        self.assertEqual({"readOnly": True, "isError": True}, self.host.last_text_field_flags)

    def test_the_notebook_spelling_is_a_modifier(self):
        Modifier = self.register_empty()
        field = self.text_input.TextFieldState("hi")
        self.material3.TextField(state=field, modifier=Modifier.padding(8))
        self.assertEqual("padding(8.0)", self.host.last_text_field_modifier)

    def test_text_state_is_not_a_parameter(self):
        field = self.text_input.TextFieldState("hi")
        with self.assertRaises(TypeError):
            self.material3.TextField(text_state=field)
        self.assertEqual([], self.host.composable_calls)

    def test_padding_is_not_a_parameter(self):
        field = self.text_input.TextFieldState("hi")
        with self.assertRaises(TypeError):
            self.material3.TextField(state=field, padding=8)

    def test_a_value_still_reaches_the_string_overload(self):
        self.material3.TextField(value="x")
        self.assertEqual(["TextField__String"], self.host.composable_calls)


if __name__ == "__main__":
    unittest.main()
