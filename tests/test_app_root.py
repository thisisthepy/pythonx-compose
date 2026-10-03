"""`@app`, `state` and `app_root` in `pythonx.compose.runtime` (issue #11, docs/INTENT.md section 5.1).

The host draws with `PythonContent("pythonx.compose.runtime", "app_root")`: it reads the module
attribute `app_root`, a Compose State whose `.value` is a zero-argument callable or None. `@app`
writes that value, so redeclaring the root replaces the screen; there is no update function.

The state itself comes from the binder's `androidx.compose.runtime.mutableStateOf`, through one
internal function, `_new_state`. Calling it from Python is python-multiplatform #38 and has not
landed, so the logic here runs against `FakeState`, patched in for `_new_state` and kept in this
file: a pure-Python state in shipped code would not make Compose recompose, so none ships.
`TheBinderPath` runs the real `_new_state` through the binder's Python layer and `fake_host.py`,
whose `mutableStateOf` and `MutableState.value` rows are shaped after python-multiplatform
`31c092f0` (#38). It skips only while the installed table binds no `mutableStateOf`.
"""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402

NEEDS_38 = "needs python-multiplatform #38"


class FakeState:
    """Test-only stand-in for a Compose `MutableState`: `.value`, and a log of writes."""

    def __init__(self, initial):
        self.writes = [initial]
        self._value = initial

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new):
        self._value = new
        self.writes.append(new)


def fresh_runtime():
    """Import `pythonx.compose.runtime` afresh, so `app_root` has not been created yet."""
    for name in [n for n in sys.modules if n == "pythonx.compose.runtime"]:
        del sys.modules[name]
    return importlib.import_module("pythonx.compose.runtime")


class TheLogic(unittest.TestCase):
    def setUp(self):
        saved = dict(sys.modules)
        self.addCleanup(lambda: (sys.modules.clear(), sys.modules.update(saved)))
        self.runtime = fresh_runtime()
        self.created = []

        def factory(initial):
            made = FakeState(initial)
            self.created.append(made)
            return made

        patcher = mock.patch.object(self.runtime, "_new_state", factory)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_app_returns_the_function_unchanged(self):
        def Screen():
            """A screen."""

        self.assertIs(Screen, self.runtime.app(Screen))
        self.assertEqual("Screen", Screen.__name__)

    def test_app_root_is_created_lazily_and_once(self):
        self.assertEqual([], self.created)
        first = self.runtime.app_root
        self.assertEqual(1, len(self.created))
        self.assertIs(first, self.runtime.app_root)
        self.assertEqual(1, len(self.created))
        self.assertIn("app_root", vars(self.runtime), "after the first read it is a plain attribute")

    def test_before_any_declaration_the_root_is_none(self):
        self.assertIsNone(self.runtime.app_root.value)

    def test_app_sets_the_root_value(self):
        @self.runtime.app
        def Screen():
            return "one"

        self.assertIs(Screen, self.runtime.app_root.value)

    def test_redeclaring_replaces_the_value_in_the_same_state(self):
        root = self.runtime.app_root

        @self.runtime.app
        def Screen():
            return "one"

        @self.runtime.app
        def Screen():  # noqa: F811
            return "two"

        self.assertIs(root, self.runtime.app_root)
        self.assertEqual("two", root.value())
        self.assertEqual(1, len(self.created))
        self.assertEqual(3, len(root.writes))

    def test_state_round_trips_through_value(self):
        counter = self.runtime.state(0)
        self.assertEqual(0, counter.value)
        counter.value = 5
        self.assertEqual(5, counter.value)

    def test_each_state_call_makes_its_own_state(self):
        self.assertIsNot(self.runtime.state(0), self.runtime.state(0))

    def test_no_update_or_refresh_name_is_public(self):
        public = [n for n in dir(self.runtime) if not n.startswith("_")]
        for name in public:
            for banned in ("update", "refresh", "invalidate", "rerender"):
                self.assertNotIn(banned, name.lower())
        for banned in ("update", "refresh", "_update", "_refresh"):
            self.assertNotIn(banned, vars(self.runtime))

    def test_dir_lists_the_new_names(self):
        for name in ("app", "state", "app_root", "Composable"):
            self.assertIn(name, dir(self.runtime))

    def test_unknown_names_still_go_to_the_reexport_path(self):
        # AttributeError with a binder; RuntimeError ("not installed") without one -- both come from
        # the reexport path, which is what answered.
        with self.assertRaises((AttributeError, RuntimeError)):
            self.runtime.no_such_name_anywhere  # noqa: B018


class TheStateFactory(unittest.TestCase):
    """`_new_state` asks the binder for `mutableStateOf` and never invents a state of its own."""

    def setUp(self):
        saved = dict(sys.modules)
        self.addCleanup(lambda: (sys.modules.clear(), sys.modules.update(saved)))
        self.runtime = fresh_runtime()

    def _binder_with(self, **names):
        module = types.ModuleType("androidx.compose.runtime")
        for key, value in names.items():
            setattr(module, key, value)
        parent = types.ModuleType("androidx.compose")
        parent.runtime = module
        top = types.ModuleType("androidx")
        top.compose = parent
        return mock.patch.dict(
            sys.modules,
            {"androidx": top, "androidx.compose": parent, "androidx.compose.runtime": module},
        )

    def test_it_calls_the_binders_mutable_state_of(self):
        seen = []
        with self._binder_with(mutableStateOf=lambda initial: seen.append(initial) or "STATE"):
            self.assertEqual("STATE", self.runtime._new_state(7))
        self.assertEqual([7], seen)

    def test_a_binder_without_mutable_state_of_raises_pointing_at_38(self):
        with self._binder_with():
            with self.assertRaises(RuntimeError) as raised:
                self.runtime._new_state(0)
        self.assertIn("#38", str(raised.exception))

    def test_no_binder_at_all_raises_pointing_at_38(self):
        with mock.patch.dict(sys.modules, {"androidx": None}):
            with self.assertRaises(RuntimeError) as raised:
                self.runtime._new_state(0)
        self.assertIn("#38", str(raised.exception))

    def test_state_and_app_root_use_the_factory_not_a_python_stand_in(self):
        with self._binder_with():
            with self.assertRaises(RuntimeError):
                self.runtime.state(0)
            with self.assertRaises(RuntimeError):
                self.runtime.app_root  # noqa: B018
        self.assertNotIn("app_root", vars(self.runtime), "a failed creation must not be cached")


class TheBinderPath(unittest.TestCase):
    """The real `_new_state`, unpatched, through the binder's Python layer and the fake host.

    The host's `mutableStateOf` / `MutableState.value` rows are shaped after python-multiplatform
    `31c092f0` (#38), so this proves the Python half: the proxy, the `value` property, the `Any?`
    slot. It skips while the installed table binds no `androidx.compose.runtime.mutableStateOf`.
    That Compose itself observes the write is the E2E module (python-multiplatform #26, issue #19).
    """

    def setUp(self):
        try:
            self.binding = adapter_loader.install()
        except adapter_loader.AdapterUnavailable as unavailable:
            self.skipTest(str(unavailable))
        if not hasattr(self.binding, "_PROPERTIES"):
            self.skipTest(NEEDS_38 + ": this binder serves no property rows (`MutableState.value`)")
        self.host = fake_host.FakeHost()
        self.host.bind()
        self.host.register(self.binding)
        self.addCleanup(self.host.unbind)
        self.addCleanup(adapter_loader.uninstall)
        try:
            kotlin_runtime = importlib.import_module("androidx.compose.runtime")
            kotlin_runtime.mutableStateOf
        except (ImportError, AttributeError):
            self.skipTest(NEEDS_38)
        self.runtime = fresh_runtime()

    def test_app_root_is_a_compose_state_the_declaration_writes(self):
        @self.runtime.app
        def Screen():
            return None

        self.assertIs(Screen, self.runtime.app_root.value)

        @self.runtime.app
        def Screen():  # noqa: F811
            return None

        self.assertIs(Screen, self.runtime.app_root.value)

    def test_app_root_is_a_binder_state_proxy(self):
        root = self.runtime.app_root
        self.assertEqual("androidx.compose.runtime.MutableState", type(root)._kotlin_type_name)
        self.assertIsNone(root.value)
        self.assertIs(root, self.runtime.app_root)

    def test_redeclaring_replaces_the_value_in_the_same_host_state(self):
        root = self.runtime.app_root

        @self.runtime.app
        def Screen():
            return "one"

        @self.runtime.app
        def Screen():  # noqa: F811
            return "two"

        self.assertEqual("two", root.value())
        self.assertEqual(3, len(self.host_states()[0].writes))

    def host_states(self):
        return [o for o in self.host._handles.values() if isinstance(o, fake_host.StubState)]

    def test_state_round_trips_through_the_binder(self):
        label = self.runtime.state("a")
        label.value = "b"
        self.assertEqual("b", label.value)
        self.assertEqual(["a", "b"], self.host_states()[0].writes)

    def test_an_int_state_is_refused_by_the_binder_not_papered_over(self):
        # `PythonxAdapter._coerce`: an int in an `Any?` slot would cross as an object handle, so the
        # binder refuses it. `state(1)` is therefore an error today; `pythonx` does not box it.
        with self.assertRaises(TypeError) as raised:
            self.runtime.state(1)
        self.assertIn("int", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
