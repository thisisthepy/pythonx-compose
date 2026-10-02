"""The manifest this package owes, pinned against the two things that consume it.

`pythonx-map.toml` is the only reason `python-multiplatform` no longer has to know Compose exists.
Two different readers use it -- the runtime adapter, through whatever an embedder installs, and the
`.pyi` generator -- so the failure it exists to prevent is the two disagreeing about a module name.
That is not hypothetical: the binder used to derive names by prefix substitution, which cannot drop
`foundation.` from the middle of `androidx.compose.foundation.layout`, so the stubs said
`pythonx.compose.layout` and the interpreter refused it.

`UI.ipynb` is the specification these tests read the expected names out of, rather than restating
them, so a notebook edit that adds an import fails here until the map covers it.
"""

from __future__ import annotations

import json
import re
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAP = REPO / "pythonx" / "compose" / "pythonx-map.toml"
NOTEBOOK = REPO / "UI.ipynb"


def _manifest() -> dict:
    with MAP.open("rb") as handle:
        return tomllib.load(handle)


def _notebook_imports() -> set[str]:
    if not NOTEBOOK.is_file():
        return set()
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    found: set[str] = set()
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        found.update(re.findall(r"from (pythonx[\w.]*) import", source))
        found.update(re.findall(r"^import (pythonx[\w.]*)", source, re.MULTILINE))
    return found


class TestManifestShipsWithThePackage(unittest.TestCase):
    def test_the_manifest_exists_and_parses(self) -> None:
        self.assertTrue(MAP.is_file(), f"{MAP.name} is what this package owes the binder")
        manifest = _manifest()
        self.assertIn("modules", manifest)
        self.assertIn("value-classes", manifest)

    def test_the_wheel_is_configured_to_carry_it(self) -> None:
        with (REPO / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        package_data = project["tool"]["setuptools"]["package-data"]
        patterns = [p for entry in package_data.values() for p in entry]
        self.assertIn("pythonx-map.toml", patterns, "a manifest nobody installs helps nobody")


class TestEveryNotebookImportIsMapped(unittest.TestCase):
    def test_the_specification_resolves(self) -> None:
        if not NOTEBOOK.is_file():
            self.skipTest("UI.ipynb is not here (it lives only in the maintainer's main checkout)")
        modules = _manifest()["modules"]
        missing = sorted(name for name in _notebook_imports() if name not in modules)
        self.assertEqual([], missing, "UI.ipynb imports a module the manifest does not map")

    def test_the_short_layout_spelling_drops_foundation(self) -> None:
        # The case that proves a prefix substitution cannot do this job.
        modules = _manifest()["modules"]
        self.assertEqual(
            "androidx.compose.foundation.layout",
            modules["pythonx.compose.layout"],
            "the rename in the middle of the name is the whole reason this file exists",
        )


class TestAliasSection(unittest.TestCase):
    def test_every_alias_points_between_mapped_modules(self) -> None:
        manifest = _manifest()
        modules = manifest["modules"]
        for owner, sources in manifest.get("aliases", {}).items():
            with self.subTest(owner=owner):
                self.assertIn(owner, modules)
                for source in sources:
                    self.assertIn(source, modules)

    def test_material3_answers_for_the_layout_composables_the_notebook_imports(self) -> None:
        aliases = _manifest()["aliases"]["pythonx.compose.material3"]["pythonx.compose.layout"]
        self.assertEqual(["Column", "Row", "Spacer"], aliases)


class TestValueClassSection(unittest.TestCase):
    def test_dp_is_allowed_and_packed_classes_are_not(self) -> None:
        allowed = _manifest()["value-classes"]["raw-primitive-allowed"]
        self.assertIn("androidx.compose.ui.unit.Dp", allowed)
        for packed in ("androidx.compose.ui.graphics.Color", "androidx.compose.ui.unit.TextUnit"):
            self.assertNotIn(
                packed,
                allowed,
                f"{packed} packs several fields into one value; a raw number decodes as something else",
            )


if __name__ == "__main__":
    unittest.main()
