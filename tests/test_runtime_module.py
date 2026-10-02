"""`pythonx/compose/runtime/__init__.py` -- the 2024 `Composable` class, gone, and what is left.

## What used to be here, and why it never ran

A decorator class (`Composable`) holding one `__composer`, plus `ComposeApp`, `KotlinComposable`,
`KotlinWidget` and a `CoroutineScope` family, all built on `jclass` --
`_runtime = jclass("io.github.thisisthepy.pycomposeui.RuntimeKt")` -- chaquopy's name-based
Java/Kotlin class lookup. `jclass` is never imported in this module, in any commit where the module
had content, so every one of those five module-level statements raised `NameError` before a single
class body executed:

    >>> from pythonx.compose.runtime import Composable
    NameError: name 'jclass' is not defined

That is not incidental breakage, it is a different technology than this repository now targets.
`jclass` is chaquopy's global; `PythonMultiplatform`'s binder is a different bridge
(`docs/pythonx-adapter-design.md` §5.1 reads the same class as "the 2024 `Composable` class", and
`agent-rules.md` §12 retires name-based JVM lookup by name). `Composable.__call__`'s other job --
inspecting `self.compose.__code__.co_varnames` to find where `content` sits -- is retired for the
same reason `modifier.py`'s mangled-suffix search was: `docs/pythonx-adapter-design.md` §5.6/§7
record that composer threading, `$changed` and `$default` are now arithmetic
`python_multiplatform.binding._bind_composable` does from a slot's *declared type*, uniformly, for a content lambda
exactly as for any other parameter -- there is nothing left for a Python-side base class to detect.

## What is left

One identity decorator, `Composable`, kept because `UI.ipynb` writes `@Composable` on every
screen-defining function and that surface is one an application author should keep being able to
write. Nothing needs to happen to the decorated function for it to work: the composer any nested
`pythonx.compose.*` call needs comes from `PythonComposition`'s push/pop around the whole exec pass
and from the *callee's* slot type, never from the caller.

## How it is reached

By its own dotted name, with the binder installed: `TheModuleIsTheFileOnDisk` below. This used to
assert the opposite, because the binder owned `sys.modules['pythonx']` with `__path__ = []`.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tokenize
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RUNTIME_PY = REPO / "pythonx" / "compose" / "runtime" / "__init__.py"


def load_by_path(path, name):
    """Load a `pythonx/...` file without importing its package, for the tests that need no binder."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheModuleIsTheFileOnDisk(unittest.TestCase):
    """`import pythonx.compose.runtime` loads this repository's file, with the binder installed.

    The binder used to own `sys.modules['pythonx']` with `__path__ = []`, and this class asserted
    the resulting unreachability. PythonMultiplatform `d00f413f` moved its layer to
    `python_multiplatform.binding`; `pythonx` is this package (AGENTS.md section 12).
    """

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

    def test_import_pythonx_compose_runtime_loads_the_file_on_disk(self):
        import pythonx.compose.runtime as runtime

        self.assertEqual(RUNTIME_PY, Path(runtime.__file__).resolve())
        self.assertTrue(callable(runtime.Composable))

    def test_pythonx_compose_is_a_package_on_disk(self):
        import pythonx.compose as compose

        self.assertEqual([str(REPO / "pythonx" / "compose")], [str(Path(p).resolve()) for p in compose.__path__])


class TheRuntimeSeam(unittest.TestCase):
    """What `Composable` does once loaded by path: nothing to the function it decorates."""

    def setUp(self):
        self.runtime = load_by_path(RUNTIME_PY, "_repo_runtime")

    def test_composable_is_importable_and_callable(self):
        self.assertTrue(callable(self.runtime.Composable))

    def test_composable_returns_the_exact_function_it_decorated(self):
        def Screen():
            return "drawn"

        decorated = self.runtime.Composable(Screen)
        self.assertIs(decorated, Screen, "Composable must not wrap or replace the function")

    def test_a_composable_function_still_runs_and_returns_its_own_value(self):
        @self.runtime.Composable
        def Screen():
            return 42

        self.assertEqual(42, Screen())

    def test_composable_preserves_name_and_doc_because_it_does_not_wrap(self):
        @self.runtime.Composable
        def Screen():
            """A screen."""

        self.assertEqual("Screen", Screen.__name__)
        self.assertEqual("A screen.", Screen.__doc__)


class TheChaquopyMechanismIsGone(unittest.TestCase):
    """No `jclass`, no base class to inherit, no `co_varnames` content-slot detection."""

    def setUp(self):
        # Code only, the same tokenising `test_modifier_module.TheShellIsGone` uses -- the module
        # docstring has to name the very things this bans in order to explain why, so a raw
        # substring check would fail on its own warning.
        raw = RUNTIME_PY.read_text(encoding="utf-8")
        kept = []
        for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                continue
            kept.append(tok.string)
        self.source = " ".join(kept)

    def test_no_chaquopy_lookup_survives(self):
        for banned in ("jclass", "ComposeApp", "KotlinComposable", "KotlinWidget",
                       "CoroutineScope", "ComposableLambdaImpl", "composableWrapper"):
            self.assertNotIn(banned, self.source, f"{banned} is 2024 chaquopy-era code")

    def test_no_content_slot_is_detected_by_inspecting_code_objects(self):
        for banned in ("co_varnames", "__composer", "_register_composer"):
            self.assertNotIn(banned, self.source, f"{banned} is the retired composer-threading path")

    def test_composable_takes_no_arguments_beyond_the_target(self):
        import inspect

        runtime = load_by_path(RUNTIME_PY, "_repo_runtime_sig")
        sig = inspect.signature(runtime.Composable)
        self.assertEqual(1, len(sig.parameters), "an identity decorator needs exactly one parameter")


if __name__ == "__main__":
    unittest.main()
