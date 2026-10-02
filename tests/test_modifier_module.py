"""`pythonx/compose/ui/modifier.py` -- the seam, and the shell it replaced.

Two things are asserted here and they matter in opposite directions.

**That the file does something.** `install()` is what makes `Modifier.padding(16).size(24)` work
from the class object; without it the layer refuses, by design, rather than guessing where an empty
`Modifier` comes from.

**That the file does almost nothing.** The 2024 version was a per-declaration wrapper and the whole
adaptation design exists to make those unnecessary, so this checks that no `def padding` has crept
back and that the mangled-name prefix search is gone. That search
(`name.startswith("Button-")`) is what the 2024 tree was stuck on, and it cannot be made to work:
Kotlin's value-class mangling suffix hashes the signature only, so `padding`, `size`, `width` and
`height` all end `-3ABfNKs`.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter as adapter_loader  # noqa: E402
import fake_host  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
MODIFIER_PY = REPO / "pythonx" / "compose" / "ui" / "modifier.py"


class TheModifierSeam(unittest.TestCase):

    def setUp(self):
        try:
            self.binding = adapter_loader.install()
        except adapter_loader.AdapterUnavailable as unavailable:
            self.skipTest(str(unavailable))
        self.host = fake_host.FakeHost()
        self.host.bind()
        self.host.register(self.binding)
        import pythonx.compose.ui.modifier as modifier

        self.modifier = modifier
        self.addCleanup(self.host.unbind)
        self.addCleanup(adapter_loader.uninstall)

    def describe(self, modifier):
        import pythonx.compose.ui as ui

        return ui.describe_modifier(modifier)

    def test_install_returns_the_same_proxy_the_module_import_gives(self):
        import pythonx.compose.ui as ui

        installed = self.modifier.install(fake_host.EMPTY_MODIFIER)
        self.assertIs(ui.Modifier, installed)

    def test_the_chain_runs_from_the_class_object_once_installed(self):
        Modifier = self.modifier.install(fake_host.EMPTY_MODIFIER)
        self.assertEqual(
            "padding(16.0) -> size(24.0)", self.describe(Modifier.padding(16).size(24))
        )
        self.assertEqual(["padding__Dp", "size__Dp"], self.host.calls)

    def test_the_module_level_modifier_attribute_resolves_lazily(self):
        self.modifier.install(fake_host.EMPTY_MODIFIER)
        self.assertIs(self.modifier.Modifier, self.modifier.modifier_type())

    def test_without_a_layer_it_says_the_host_never_installed_one(self):
        adapter_loader.uninstall()
        with self.assertRaises(RuntimeError) as raised:
            self.modifier.adapter()
        self.assertIn("PythonxAdapter.install()", str(raised.exception))

    def test_the_placeholder_factory_is_labelled_as_unbound(self):
        """It is not a working default and the file must not pretend it is."""
        self.assertEqual("androidx.compose.ui.emptyModifier",
                         self.modifier.PLACEHOLDER_EMPTY_FACTORY)
        # The constant's own docstring, read from source. Python attaches no `__doc__` to a
        # module-level name, so asking the module for it returns the *module* docstring and the
        # assertion passes or fails on unrelated prose.
        source = MODIFIER_PY.read_text(encoding="utf-8")
        after = source.split("PLACEHOLDER_EMPTY_FACTORY =", 1)[1]
        self.assertIn("not** bound", after.split("\n\n", 1)[0])


class TheShellIsGone(unittest.TestCase):
    """No per-declaration wrapper, and no mangled-name prefix search."""

    def setUp(self):
        # Code only. The module docstring names the very things this class bans -- it has to, since
        # it explains why they are banned -- so reading the raw file makes the guard fail on the
        # warning against the mistake rather than on the mistake. Strings and comments are stripped
        # by tokenising, which also means a banned name inside a future comment cannot mask itself.
        import io, tokenize

        raw = MODIFIER_PY.read_text(encoding="utf-8")
        kept = []
        for tok in tokenize.generate_tokens(io.StringIO(raw).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                continue
            kept.append(tok.string)
        self.source = " ".join(kept)

    def test_no_composable_wrapper_survives(self):
        for banned in ("__COMPILED_CODE__", "c=self.composer", "changed=1", "def compose("):
            self.assertNotIn(banned, self.source, f"{banned} is 2024 wrapper code")

    def test_no_declaration_is_named_in_python(self):
        for banned in ("def padding", "def fill_max_size", "def size", "ButtonKt"):
            self.assertNotIn(banned, self.source, f"{banned} would be per-declaration Python")

    def test_no_name_is_looked_up_by_its_mangled_jvm_spelling(self):
        self.assertNotIn('startswith("Button-")', self.source)
        self.assertNotIn(".__dict__.items()", self.source)


if __name__ == "__main__":
    unittest.main()
