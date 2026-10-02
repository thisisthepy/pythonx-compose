"""Pythonic stubs from the binder's Kotlin-named ones, by the rule the runtime resolves names with.

The input here is a fixture shaped like python-multiplatform's `PythonStubsTask` output, holding the
same declarations `fake_host.py` binds. So the second class can do what a stub is for and check it:
the signature an editor reads from the stub is the signature `inspect.signature` reports at run time.
"""

from __future__ import annotations

import ast
import inspect
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402
import gen_stubs  # noqa: E402

KOTLIN_STUBS = HERE / "fixtures" / "kotlin_stubs"
PACKAGE = REPO / "pythonx"


def _generated() -> dict[Path, str]:
    return gen_stubs.generate(KOTLIN_STUBS, PACKAGE)


def _functions(text: str) -> dict[str, list[ast.FunctionDef]]:
    found: dict[str, list[ast.FunctionDef]] = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef):
            found.setdefault(node.name, []).append(node)
    return found


def _parameter_names(function: ast.FunctionDef) -> list[str]:
    a = function.args
    return [p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)]


LAYOUT = PACKAGE / "compose" / "foundation" / "layout" / "__init__.pyi"


class TheConversion(unittest.TestCase):

    def setUp(self):
        self.stubs = _generated()

    def test_every_manifest_module_gets_a_stub_beside_its_init(self):
        for module_name in gen_stubs.manifest()["modules"]:
            path = PACKAGE.joinpath(*module_name.split(".")[1:]) / "__init__.pyi"
            with self.subTest(module=module_name):
                self.assertIn(path, self.stubs)

    def test_names_and_parameters_follow_the_runtime_rule(self):
        functions = _functions(self.stubs[LAYOUT])
        self.assertIn("padding_values_of", functions)
        self.assertIn("fill_max_width", functions)
        self.assertNotIn("paddingValuesOf", functions)
        self.assertEqual(["receiver", "padding_values"], _parameter_names(functions["padding__PaddingValues"][0]))

    def test_an_overload_set_gets_its_base_name_as_overloads(self):
        padding = _functions(self.stubs[LAYOUT])["padding"]
        self.assertEqual(4, len(padding))
        for variant in padding:
            self.assertEqual(["overload"], [ast.unparse(d) for d in variant.decorator_list])

    def test_anonymous_and_receiver_slots_keep_their_names(self):
        scan = _functions(self.stubs[LAYOUT])["scan"][0]
        self.assertEqual(["receiver", "first", "__a1", "last"], _parameter_names(scan))

    def test_a_nested_object_stub_is_converted_one_level_down(self):
        nested = PACKAGE / "compose" / "foundation" / "layout" / "Arrangement" / "__init__.pyi"
        self.assertIn("SpaceBetween: int", self.stubs[nested])

    def test_names_the_package_defines_itself_are_carried_over(self):
        runtime = self.stubs[PACKAGE / "compose" / "runtime" / "__init__.pyi"]
        self.assertIn("def Composable(target)", runtime)

    def test_every_stub_is_valid_python(self):
        for path, text in self.stubs.items():
            with self.subTest(stub=str(path.relative_to(REPO))):
                compile(text, str(path), "exec")


class TheStubMatchesTheRuntime(unittest.TestCase):
    """What an editor reads from the stub is what `inspect.signature` reports at run time."""

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

    def test_each_single_declaration_has_the_same_parameter_names(self):
        import pythonx.compose.foundation.layout as layout

        functions = _functions(_generated()[LAYOUT])
        for name in ("padding__Dp", "padding__Dp_Dp", "padding__PaddingValues", "padding_values_of",
                     "size__Dp", "fill_max_width"):
            with self.subTest(name=name):
                runtime = list(inspect.signature(getattr(layout, name)).parameters)
                self.assertEqual(runtime, _parameter_names(functions[name][0]))


if __name__ == "__main__":
    unittest.main()
