"""`remember_saveable` and the notebook's state spelling (issue #102, docs/INTENT.md section 5.9, SPEC S5.6).

`UI.ipynb` cells 9 to 13 read `main.App.messages`, `main.App.messages.getValue()` and
`main.App.messages.setValue(...)`. The 2024 demo the notebook ran against attached that state to its
root itself (`cls.messages = messages = remember_saveable("")`), and so does an app here:
`App.messages = messages = remember_saveable("")` inside `def App():`.

`remember_saveable(initial)` calls the host's `@Composable` `rememberSaveableWrapper(initial)`
(python-multiplatform-compose, python-multiplatform #174, `8c56f19b`), which picks the Kotlin state
from the boxed value's type (Int, Long, Double, Boolean, String) and refuses any other. It returns a
thin wrapper over the Kotlin `MutableState` with `getValue()`, `setValue(value)` and `.value`, each
going through `MutableState.value`.

These tests run against `tests/fake_host.py`, whose `rememberSaveableWrapper` row is shaped after
that function. What they prove is the Python half: the value reaches Kotlin as it is, the wrapper
over one state, the error outside a composition, and an app root that carries its state. The type
dispatch, and that Compose keeps the state across recomposition, rotation and process restart, are
python-multiplatform's proof (`RememberSaveableRenderTest`), not this file's.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fake_host  # noqa: E402
from test_chain import AdapterCase  # noqa: E402


class SaveableCase(AdapterCase):

    def setUp(self):
        super().setUp()
        if not hasattr(self.binding, "push_composer"):
            self.skipTest("the binder has no @Composable binding (push_composer)")
        if not hasattr(self.binding, "_box_scalar"):
            self.skipTest("needs python-multiplatform #69 (scalar boxing for Any slots)")
        # A composition is running: composable rows read the composer `push_composer` was given.
        self.binding.push_composer(self.host.composer())
        self.addCleanup(self.binding.pop_composer)
        import pythonx.compose.runtime as runtime

        self.runtime = runtime

    def outside_the_composition(self):
        """Leave the composition, as a notebook cell does, and come back for cleanup."""
        self.binding.pop_composer()
        self.addCleanup(lambda: self.binding.push_composer(self.host.composer()))

    def host_states(self):
        return [o for o in self.host._handles.values() if isinstance(o, fake_host.StubState)]


class TheValueSent(SaveableCase):
    """The initial value goes to Kotlin as it is: the type rule is `rememberSaveableWrapper`'s."""

    def test_each_supported_value_reaches_the_host_unchanged(self):
        for initial in ("", "hi", 0, 2**31 - 1, 2**31, 2**63 - 1, -(2**63), 1.5, True, False):
            with self.subTest(initial=initial):
                self.host.saveable_calls.clear()
                self.runtime.remember_saveable(initial)
                self.assertEqual([initial], self.host.saveable_calls)
                self.assertIs(type(initial), type(self.host.saveable_calls[0]))

    def test_an_int_beyond_64_bits_is_refused_before_kotlin_is_called(self):
        # The binder's own scalar boxing (python-multiplatform #69) refuses it with the reason.
        with self.assertRaises(TypeError) as raised:
            self.runtime.remember_saveable(2**64)
        self.assertIn("64 bits", str(raised.exception))
        self.assertEqual([], self.host.saveable_calls)


class TheWrapper(SaveableCase):
    """`getValue()`, `setValue(value)` and `.value` are one Kotlin state."""

    def test_the_three_spellings_read_and_write_one_state(self):
        messages = self.runtime.remember_saveable("a")
        self.assertEqual("a", messages.getValue())
        self.assertEqual("a", messages.value)
        messages.setValue("b")
        self.assertEqual("b", messages.value)
        messages.value = "c"
        self.assertEqual("c", messages.getValue())
        (state,) = self.host_states()
        self.assertEqual(["a", "b", "c"], state.writes)

    def test_every_read_goes_to_the_kotlin_state(self):
        # Nothing is cached in Python: a write Kotlin made is what the next read returns, so the
        # read Compose records is the one the composition makes.
        count = self.runtime.remember_saveable(1)
        (state,) = self.host_states()
        state.write(41)
        self.assertEqual(41, count.getValue())
        self.assertEqual(41, count.value)

    def test_scalars_keep_their_python_type(self):
        for initial in (7, 2**40, 2.5, True, "text"):
            with self.subTest(initial=initial):
                held = self.runtime.remember_saveable(initial)
                self.assertIs(type(initial), type(held.getValue()))

    def test_it_is_reached_from_pythonx_compose_runtime(self):
        from pythonx.compose.runtime import remember_saveable

        self.assertIs(self.runtime.remember_saveable, remember_saveable)
        self.assertIn("remember_saveable", dir(self.runtime))


class OutsideTheComposition(SaveableCase):

    def test_remember_saveable_needs_a_composition(self):
        self.outside_the_composition()
        with self.assertRaises(RuntimeError):
            self.runtime.remember_saveable("")


class TheNotebookSpelling(SaveableCase):
    """Cells 9 to 13, against an app that attaches its state the way the 2024 demo did."""

    def declare_app(self):
        runtime = self.runtime

        @runtime.app
        @runtime.Composable
        def App():
            App.messages = messages = runtime.remember_saveable("안녕하세요")
            return messages.getValue()

        return App

    def test_cells_9_to_13_read_and_write_the_roots_state(self):
        App = self.declare_app()
        self.assertIs(App, self.runtime.app_root.value)
        App()  # the host composes the declared root
        self.outside_the_composition()  # a notebook cell runs outside it

        self.assertIsNotNone(App.messages)  # cell 9
        message_backup = App.messages.getValue()  # cell 10
        self.assertEqual("안녕하세요", message_backup)
        App.messages.setValue("UI 상태를 변경해보는 테스트입니다.")  # cell 12
        self.assertEqual("UI 상태를 변경해보는 테스트입니다.", App.messages.value)
        App.messages.setValue(message_backup)  # cell 13
        self.assertEqual("안녕하세요", App.messages.getValue())
        (state,) = self.host_states()[-1:]
        self.assertEqual(["안녕하세요", "UI 상태를 변경해보는 테스트입니다.", "안녕하세요"], state.writes)

    def test_before_the_first_composition_the_root_has_no_state_yet(self):
        App = self.declare_app()
        self.assertFalse(hasattr(App, "messages"))


if __name__ == "__main__":
    unittest.main()
