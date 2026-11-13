"""The fork's design systems as `pythonx.compose` modules, and the layered `material3` row (#152, #54).

Owner decision, 2026-11-13 (relayed by the leader, recorded on #54): `pythonx.compose.material3` maps
to the fork's design-system package `org.thisisthepy.compose.material3`, and the other design systems
(`breeze`, `cupertino`, `deepin`, `fluent`, `gnome`, `liquid-glass`, on
`org.thisisthepy.compose.designsystem`) are exposed the same way, each with a regression guard.

The means below are an agent proposal, not confirmed by the owner (SPEC S2.1):

- A manifest row may list several Kotlin packages, searched in order, first match wins. `UI.ipynb`
  imports `Text`, `Button`, `Card`, `TextField` from `pythonx.compose.material3`, which only
  `androidx.compose.material3` declares, so that package stays as the second layer.
- A listed package the binder does not serve is skipped (none of the design systems is on Maven
  Central yet).
- The surface guard: a committed snapshot of each guarded module's public surface.
"""

from __future__ import annotations

import sys
import tempfile
import tomllib
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import gen_stubs  # noqa: E402
import surface  # noqa: E402
from pythonx.compose import _reexport  # noqa: E402

MAP = REPO / "pythonx" / "compose" / "pythonx-map.toml"
SURFACES = HERE / "fixtures" / "surfaces"

DESIGN_SYSTEMS = {
    "pythonx.compose.designsystem": "org.thisisthepy.compose.designsystem",
    "pythonx.compose.breeze": "org.thisisthepy.compose.breeze",
    "pythonx.compose.cupertino": "org.thisisthepy.compose.cupertino",
    "pythonx.compose.deepin": "org.thisisthepy.compose.deepin",
    "pythonx.compose.fluent": "org.thisisthepy.compose.fluent",
    "pythonx.compose.gnome": "org.thisisthepy.compose.gnome",
    "pythonx.compose.liquidglass": "org.thisisthepy.compose.liquidglass",
}


def _manifest() -> dict:
    with MAP.open("rb") as handle:
        return tomllib.load(handle)


class TheRows(unittest.TestCase):
    def test_material3_searches_the_design_system_first_then_material3_itself(self) -> None:
        self.assertEqual(
            ["org.thisisthepy.compose.material3", "androidx.compose.material3"],
            _manifest()["modules"]["pythonx.compose.material3"],
        )

    def test_every_design_system_has_its_row(self) -> None:
        modules = _manifest()["modules"]
        for module, package in DESIGN_SYSTEMS.items():
            with self.subTest(module=module):
                self.assertEqual(package, modules.get(module))

    def test_a_row_is_a_package_or_a_non_empty_list_of_distinct_packages(self) -> None:
        for module, row in _manifest()["modules"].items():
            with self.subTest(module=module):
                if isinstance(row, str):
                    continue
                self.assertIsInstance(row, list)
                self.assertTrue(row, "an empty list maps the module to nothing")
                self.assertTrue(all(isinstance(package, str) for package in row))
                self.assertEqual(len(set(row)), len(row))

    def test_the_runtime_reads_a_row_as_its_ordered_packages(self) -> None:
        self.assertEqual(
            ("org.thisisthepy.compose.material3", "androidx.compose.material3"),
            _reexport.kotlin_packages_of("pythonx.compose.material3"),
        )
        self.assertEqual(
            ("androidx.compose.foundation.layout",), _reexport.kotlin_packages_of("pythonx.compose.layout")
        )


class _FakeBinding(types.ModuleType):
    """Only what `_reexport._prime` touches."""

    def __init__(self) -> None:
        super().__init__(_reexport.BINDING_MODULE)
        self._EMPTY_FACTORIES: dict[str, object] = {}

    def allow_raw_primitive(self, kotlin_type: str) -> None:
        pass

    def register_empty(self, kotlin_type: str, factory: object) -> None:
        self._EMPTY_FACTORIES[kotlin_type] = factory


class TheRuntimeSearchesTheLayersInOrder(unittest.TestCase):
    MODULE = "pythonx.compose._layered_probe"

    def setUp(self) -> None:
        self.saved = {name: sys.modules.get(name) for name in (_reexport.BINDING_MODULE,)}
        sys.modules[_reexport.BINDING_MODULE] = _FakeBinding()
        self.addCleanup(self._restore)
        self.rows: dict[str, object] = {}
        real = _reexport.manifest()
        patched = dict(real)
        patched["modules"] = {**real["modules"], self.MODULE: ["probe.design", "probe.material"]}
        self.manifest = mock.patch.object(_reexport, "manifest", return_value=patched)
        self.manifest.start()
        self.addCleanup(self.manifest.stop)
        self.kotlin: list[str] = []

    def _restore(self) -> None:
        for name, module in self.saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        for name in [self.MODULE, *self.kotlin]:
            sys.modules.pop(name, None)

    def _kotlin(self, name: str, **declarations: object) -> None:
        module = types.ModuleType(name)
        for key, value in declarations.items():
            setattr(module, key, value)
        sys.modules[name] = module
        self.kotlin.append(name)

    def _module(self) -> types.ModuleType:
        module = types.ModuleType(self.MODULE)
        module.__path__ = []  # a package, as every pythonx.compose module is
        module.__getattr__, module.__dir__ = _reexport.reexport(self.MODULE)  # type: ignore[method-assign]
        sys.modules[self.MODULE] = module
        return module

    def test_a_name_both_layers_declare_comes_from_the_first(self) -> None:
        self._kotlin("probe.design", Button="design Button")
        self._kotlin("probe.material", Button="material Button", Text="material Text")
        self.assertEqual("design Button", self._module().Button)

    def test_a_name_only_the_later_layer_declares_comes_from_it(self) -> None:
        self._kotlin("probe.design", MaterialButton="design MaterialButton")
        self._kotlin("probe.material", Text="material Text")
        module = self._module()
        self.assertEqual("material Text", module.Text)
        self.assertEqual("design MaterialButton", module.MaterialButton)

    def test_a_layer_the_binder_does_not_serve_is_skipped(self) -> None:
        self._kotlin("probe.material", Text="material Text")
        self.assertEqual("material Text", self._module().Text)

    def test_a_name_no_layer_declares_names_every_package_searched(self) -> None:
        self._kotlin("probe.material", Text="material Text")
        with self.assertRaises(AttributeError) as raised:
            self._module().Nowhere
        self.assertIn("probe.material", str(raised.exception))

    def test_no_layer_served_is_an_attribute_error_naming_them(self) -> None:
        with self.assertRaises(AttributeError) as raised:
            self._module().Text
        self.assertIn("probe.design", str(raised.exception))
        self.assertIn("probe.material", str(raised.exception))

    def test_dir_lists_every_layer(self) -> None:
        self._kotlin("probe.design", MaterialButton="b")
        self._kotlin("probe.material", Text="t")
        listed = dir(self._module())
        self.assertIn("MaterialButton", listed)
        self.assertIn("Text", listed)


_DESIGN_STUB = '''import typing as _t

class Material3DesignSystem:
    """Kotlin: probe.design.Material3DesignSystem"""

def MaterialButton(onClick: _t.Any, enabled: bool = ...) -> None:
    """Kotlin: probe.design.MaterialButton"""
    ...

def Text(text: str) -> None:
    """Kotlin: probe.design.Text"""
    ...
'''

_MATERIAL_STUB = '''import typing as _t

def Text(text: str, fontSize: float = ...) -> None:
    """Kotlin: probe.material.Text"""
    ...

def Button(onClick: _t.Any) -> None:
    """Kotlin: probe.material.Button"""
    ...
'''


class TheGeneratorMergesTheLayers(unittest.TestCase):
    MODULE = "pythonx.compose.material3"

    def _generate(self, packages: dict[str, str], row: object) -> str:
        real = _reexport.manifest()
        patched = dict(real)
        patched["modules"] = {**real["modules"], self.MODULE: row}
        with tempfile.TemporaryDirectory() as root:
            for package, text in packages.items():
                path = Path(root).joinpath(*package.split(".")) / "__init__.pyi"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            with mock.patch.object(gen_stubs, "manifest", return_value=patched):
                out = gen_stubs.generate(Path(root), REPO / "pythonx")
        return out[REPO / "pythonx" / "compose" / "material3" / "__init__.pyi"]

    def test_both_layers_are_in_the_stub_and_the_first_wins_a_shared_name(self) -> None:
        text = self._generate(
            {"probe.design": _DESIGN_STUB, "probe.material": _MATERIAL_STUB}, ["probe.design", "probe.material"]
        )
        lines = surface.surface(text)
        self.assertIn("class Material3DesignSystem", lines)
        self.assertIn("MaterialButton(on_click, enabled=...) -> None", lines)
        self.assertIn("Button(on_click) -> None", lines)
        self.assertIn("Text(text) -> None", lines, "the design system's Text shadows Material's")
        self.assertNotIn("Text(text, font_size=...) -> None", lines)

    def test_a_layer_absent_from_the_artefact_leaves_the_others(self) -> None:
        text = self._generate({"probe.material": _MATERIAL_STUB}, ["probe.design", "probe.material"])
        self.assertIn("Text(text, font_size=...) -> None", surface.surface(text))

    def test_a_single_package_row_converts_as_before(self) -> None:
        single = self._generate({"probe.material": _MATERIAL_STUB}, "probe.material")
        listed = self._generate({"probe.material": _MATERIAL_STUB}, ["probe.material"])
        # The first line names the (temporary) input directory; everything after it must match.
        self.assertEqual(single.split("\n", 1)[1], listed.split("\n", 1)[1])


_GUARDED = ("pythonx.compose.material3", *DESIGN_SYSTEMS)


def _stub(module: str) -> str:
    return (REPO.joinpath(*module.split(".")) / "__init__.pyi").read_text(encoding="utf-8")


class TheSurfaceGuard(unittest.TestCase):
    """A regenerated stub may add declarations; it may not drop or change one a snapshot records,
    unless the reviewed allowlist (`tests/fixtures/surfaces/allowlist.toml`) acknowledges that line."""

    def test_surface_reads_names_parameters_defaults_and_returns(self) -> None:
        lines = surface.surface(
            "import typing as _t\n"
            "def f(a: int, b: int = ..., *, c: str = ...) -> int: ...\n"
            "class K:\n"
            "    x: _t.ClassVar[int]\n"
            "    @staticmethod\n"
            "    def g(y: int) -> K: ...\n"
        )
        self.assertEqual(["K.g(y) -> K", "K.x: _t.ClassVar[int]", "class K", "f(a, b=..., *, c=...) -> int"], lines)

    def test_every_guarded_module_has_a_snapshot(self) -> None:
        for module in _GUARDED:
            with self.subTest(module=module):
                self.assertTrue((SURFACES / f"{module}.txt").is_file())

    def test_no_snapshot_line_is_lost(self) -> None:
        allowed = surface.allowlist(SURFACES / "allowlist.toml")
        for module in _GUARDED:
            with self.subTest(module=module):
                lost = surface.lost(
                    surface.read_snapshot(SURFACES / f"{module}.txt"),
                    surface.surface(_stub(module)),
                    allowed.get(module, set()),
                )
                self.assertEqual([], lost, f"{module} lost declarations; acknowledge them in allowlist.toml")

    def test_an_empty_snapshot_stays_empty_until_it_is_recorded(self) -> None:
        """A design system the binder does not serve yet has a header-only stub. The day it is served,
        this fails until `scripts/surface.py` records its snapshot, so the guard starts from that day."""
        for module in _GUARDED:
            snapshot = surface.read_snapshot(SURFACES / f"{module}.txt")
            if snapshot:
                continue
            with self.subTest(module=module):
                self.assertEqual([], surface.surface(_stub(module)))

    def test_the_guard_fails_on_a_dropped_or_changed_declaration(self) -> None:
        snapshot = surface.surface(_stub("pythonx.compose.material3"))
        self.assertTrue(any(line.startswith("Text(text, modifier=..., color=...") for line in snapshot))
        dropped = [line for line in snapshot if not line.startswith("Text(")]
        self.assertTrue(surface.lost(snapshot, dropped, set()))
        self.assertEqual([], surface.lost(snapshot, dropped, {l for l in snapshot if l.startswith("Text(")}))

    def test_every_allowlisted_line_has_a_reason_and_is_in_its_snapshot(self) -> None:
        with (SURFACES / "allowlist.toml").open("rb") as handle:
            entries = tomllib.load(handle).get("lost", [])
        for entry in entries:
            with self.subTest(entry=entry):
                self.assertTrue(entry.get("reason", "").strip())
                self.assertIn(entry["line"], surface.read_snapshot(SURFACES / f"{entry['module']}.txt"))


class ThePackagesOnDisk(unittest.TestCase):
    def test_every_design_system_is_a_package_that_imports_without_a_binder(self) -> None:
        import importlib

        for module in DESIGN_SYSTEMS:
            with self.subTest(module=module):
                imported = importlib.import_module(module)
                self.assertTrue(imported.__doc__ and len(imported.__doc__) > 40)


if __name__ == "__main__":
    unittest.main()
