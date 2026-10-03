"""Pythonic stubs from the binder's Kotlin-named ones, by the rule the runtime resolves names with.

The inputs here are two fixtures shaped like python-multiplatform's `PythonStubsTask` output, holding
the same declarations `fake_host.py` binds: `kotlin_stubs` in the first format (bare functions,
explicit overloads only) and `kotlin_stubs_v2` in the current one (`import typing as _t`, one stub
class per bound Kotlin type with its extension members as `ClassVar`s of callable protocols, the
binder's own `@overload` sets, Kotlin objects either as `<Object>/__init__.pyi` or as a class in the
parent stub). So `TheStubMatchesTheRuntime` can do what a stub is for and check it: the signature an
editor reads from the stub is the signature `inspect.signature` reports at run time.

`kotlin_stubs_v3` is the format of python-multiplatform #53, #44 and #38: an object stub that declares its
nested Kotlin types as classes (`End: Horizontal`), object functions as explicit overloads, and properties
with `@name.setter`.

`TheCommittedStubs` holds the stubs this repository ships to the real input, python-multiplatform's
`kotlin-stubs` artefact, when it has been downloaded to `.tmp/kotlin-stubs.zip`.
"""

from __future__ import annotations

import ast
import inspect
import sys
import tempfile
import unittest
import zipfile
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
KOTLIN_STUBS_V2 = HERE / "fixtures" / "kotlin_stubs_v2"
KOTLIN_STUBS_V3 = HERE / "fixtures" / "kotlin_stubs_v3"
KOTLIN_STUBS_V4 = HERE / "fixtures" / "kotlin_stubs_v4"
ARTEFACT = REPO / ".tmp" / "kotlin-stubs.zip"
PACKAGE = REPO / "pythonx"
COMPOSE = PACKAGE / "compose"

LAYOUT = COMPOSE / "layout" / "__init__.pyi"
LONG_LAYOUT = COMPOSE / "foundation" / "layout" / "__init__.pyi"
UI = COMPOSE / "ui" / "__init__.pyi"
TEXT = COMPOSE / "ui" / "text" / "__init__.pyi"
MATERIAL3 = COMPOSE / "material3" / "__init__.pyi"
ICONS = COMPOSE / "material" / "icons" / "__init__.pyi"


def _generated(root: Path = KOTLIN_STUBS) -> dict[Path, str]:
    return gen_stubs.generate(root, PACKAGE)


def _functions(text: str) -> dict[str, list[ast.FunctionDef]]:
    found: dict[str, list[ast.FunctionDef]] = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef):
            found.setdefault(node.name, []).append(node)
    return found


def _classes(text: str) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in ast.parse(text).body if isinstance(node, ast.ClassDef)}


def _members(cls: ast.ClassDef) -> dict[str, ast.stmt]:
    found: dict[str, ast.stmt] = {}
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found[node.target.id] = node
        elif isinstance(node, ast.FunctionDef):
            found.setdefault(node.name, node)
    return found


def _parameter_names(function: ast.FunctionDef) -> list[str]:
    a = function.args
    return [p.arg for p in (*a.posonlyargs, *a.args, *a.kwonlyargs)]


def _imports(text: str) -> list[str]:
    return [ast.unparse(node) for node in ast.parse(text).body if isinstance(node, (ast.Import, ast.ImportFrom))]


def _code_names(text: str) -> set[str]:
    """Every dotted name the stub's code (not its docstrings or comments) refers to."""
    names = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Attribute, ast.Name)):
            names.add(ast.unparse(node))
    return names


class TheConversion(unittest.TestCase):
    """The first upstream format, still converted the way it always was."""

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
            self.assertEqual(["_t.overload"], [ast.unparse(d) for d in variant.decorator_list])

    def test_overloads_come_fewest_parameters_first(self):
        """mypy takes the first matching overload, so the order is part of the contract."""
        padding = _functions(self.stubs[LAYOUT])["padding"]
        counts = [len(_parameter_names(variant)) for variant in padding]
        self.assertEqual(sorted(counts), counts)
        self.assertEqual(2, counts[0])

    def test_anonymous_and_receiver_slots_keep_their_names(self):
        scan = _functions(self.stubs[LAYOUT])["scan"][0]
        self.assertEqual(["receiver", "first", "__a1", "last"], _parameter_names(scan))

    def test_a_nested_object_stub_becomes_a_class_in_its_parent(self):
        arrangement = _classes(self.stubs[LAYOUT])["Arrangement"]
        self.assertEqual("_t.ClassVar[int]", ast.unparse(_members(arrangement)["SpaceBetween"].annotation))

    def test_names_the_package_defines_itself_are_carried_over(self):
        runtime = self.stubs[COMPOSE / "runtime" / "__init__.pyi"]
        self.assertIn("def Composable(target)", runtime)

    def test_a_public_annotated_name_the_package_declares_is_carried_over(self):
        # `runtime.app_root` is created on first read by a module `__getattr__`, so `__init__.py`
        # only annotates it; the stub must still say it exists.
        runtime = self.stubs[COMPOSE / "runtime" / "__init__.pyi"]
        self.assertIn("app_root: State", runtime)
        self.assertIn("def app(root)", runtime)
        self.assertIn("def state(initial)", runtime)

    def test_every_stub_is_valid_python(self):
        for path, text in self.stubs.items():
            with self.subTest(stub=str(path.relative_to(REPO))):
                compile(text, str(path), "exec")


class TheCurrentFormat(unittest.TestCase):
    """The current upstream format: stub classes, protocols, the binder's own overload sets."""

    def setUp(self):
        self.stubs = _generated(KOTLIN_STUBS_V2)

    def test_module_functions_and_their_parameters_follow_the_runtime_rule(self):
        functions = _functions(self.stubs[LAYOUT])
        self.assertIn("padding_values_of", functions)
        self.assertIn("fill_max_width", functions)
        self.assertNotIn("fillMaxWidth", functions)
        self.assertEqual(["receiver", "padding_values"], _parameter_names(functions["padding__PaddingValues"][0]))

    def test_keyword_only_parameters_stay_keyword_only(self):
        column = _functions(self.stubs[LAYOUT])["Column"][0]
        self.assertEqual(["modifier", "vertical_arrangement"], [a.arg for a in column.args.args])
        self.assertEqual(["content"], [a.arg for a in column.args.kwonlyargs])

    def test_the_binders_overload_set_is_kept_in_its_order(self):
        padding = _functions(self.stubs[LAYOUT])["padding"]
        self.assertEqual(
            [["receiver", "all"], ["receiver", "horizontal", "vertical"],
             ["receiver", "start", "top", "end", "bottom"], ["receiver", "padding_values"]],
            [_parameter_names(variant) for variant in padding],
        )
        for variant in padding:
            self.assertEqual(["_t.overload"], [ast.unparse(d) for d in variant.decorator_list])

    def test_the_binders_type_ignore_comments_survive(self):
        """Without them mypy reports the binder's unreachable overloads in every program that imports the stub."""
        lines = [line for line in self.stubs[LAYOUT].splitlines() if line.startswith("def padding(")]
        self.assertEqual(4, len(lines))
        self.assertNotIn("# type: ignore", lines[0])
        for line in lines[1:]:
            self.assertTrue(line.endswith("# type: ignore[overload-cannot-match]"), line)

    def test_a_stub_class_keeps_its_name_and_its_members_follow_the_member_resolver(self):
        modifier = _members(_classes(self.stubs[UI])["Modifier"])
        self.assertIn("fill_max_width", modifier)
        self.assertIn("padding__PaddingValues", modifier)
        self.assertIn("z_index", modifier)
        self.assertNotIn("fillMaxWidth", modifier)
        self.assertEqual("_t.ClassVar[_Modifier_zIndex]", ast.unparse(modifier["z_index"].annotation))

    def test_a_methods_keywords_are_snake_case_like_a_module_functions(self):
        """The runtime translates a method's keywords (SPEC S4.1); the receiver slot keeps its name."""
        protocols = _classes(self.stubs[UI])
        call = _members(protocols["_Modifier_padding__PaddingValues"])["__call__"]
        self.assertEqual(["self", "padding_values"], _parameter_names(call))
        call = _members(protocols["_Modifier_zIndex"])["__call__"]
        self.assertEqual(["self", "z_index"], _parameter_names(call))

    def test_every_protocol_parameter_is_snake_case_and_keyword_only_stays_so(self):
        names = []
        for protocol in _classes(self.stubs[UI]).values():
            for node in protocol.body:
                if isinstance(node, ast.FunctionDef) and node.name == "__call__":
                    names += [n for n in _parameter_names(node) if n != "self" and not n.startswith("__a")]
        self.assertIn("padding_values", names)
        self.assertEqual([], [n for n in names if n != gen_stubs.snake_case(n)])
        approach = _members(_classes(self.stubs[UI])["_Modifier_approachLayout"]) \
            if "_Modifier_approachLayout" in _classes(self.stubs[UI]) else None
        if approach is not None:
            self.assertTrue(approach["__call__"].args.kwonlyargs)

    def test_the_header_records_the_input_and_says_nothing_of_kotlin_keywords(self):
        header = self.stubs[UI].splitlines()[:2]
        self.assertTrue(header[0].startswith("# GENERATED by tools/gen_stubs.py"), header[0])
        self.assertNotIn("keyword", self.stubs[UI].splitlines()[1])
        self.assertNotIn("Methods are reached by", self.stubs[UI])

    def test_references_to_mapped_kotlin_packages_name_the_pythonx_module(self):
        text = self.stubs[LAYOUT]
        self.assertIn("import pythonx.compose.ui", _imports(text))
        column = _functions(text)["Column"][0]
        self.assertEqual("pythonx.compose.ui.Modifier", ast.unparse(column.args.args[0].annotation))
        self.assertFalse({name for name in _code_names(text) if name.startswith("androidx")})

    def test_the_first_manifest_module_for_a_package_is_the_one_referenced(self):
        call = _members(_classes(self.stubs[UI])["_Modifier_column"])["__call__"]
        self.assertEqual("pythonx.compose.layout.ColumnScope", ast.unparse(call.args.args[1].annotation))
        self.assertIn("import pythonx.compose.layout", _imports(self.stubs[UI]))

    def test_unmapped_or_undeclared_references_become_any(self):
        z_index_of = _functions(self.stubs[LAYOUT])["z_index_of"][0]
        self.assertEqual("_t.Any", ast.unparse(z_index_of.returns))
        self.assertNotIn("import androidx.compose.ui.draw", _imports(self.stubs[LAYOUT]))
        text = _functions(self.stubs[MATERIAL3])["Text"][0]
        annotations = {a.arg: ast.unparse(a.annotation) for a in text.args.args}
        self.assertEqual("_t.Any", annotations["inline_content"])       # kotlin.collections: unmapped
        self.assertEqual("_t.Any", annotations["style"])                # ui.text declares no ParagraphStyle
        self.assertEqual(
            "_t.Callable[[pythonx.compose.ui.text.TextLayoutResult], None] | None", annotations["on_text_layout"]
        )
        self.assertEqual(
            ["import typing as _t", "import pythonx.compose.ui", "import pythonx.compose.ui.text"],
            [
                line for line in _imports(self.stubs[MATERIAL3])
                if not line.startswith("from ") and " as _alias_" not in line  # the DefaultIcons path alias
            ],
        )

    def test_an_object_sub_package_becomes_a_class_in_its_parent(self):
        arrangement = _members(_classes(self.stubs[LAYOUT])["Arrangement"])
        self.assertEqual("_t.ClassVar[_t.Any]", ast.unparse(arrangement["SpaceBetween"].annotation))
        spaced_by = arrangement["spaced_by"]
        self.assertEqual(["staticmethod"], [ast.unparse(d) for d in spaced_by.decorator_list])
        self.assertEqual(["space"], _parameter_names(spaced_by))

    def test_an_object_already_in_its_parent_stub_is_kept(self):
        """python-multiplatform #44 moves objects into the parent stub; that layout converts the same."""
        alignment = _members(_classes(self.stubs[UI])["Alignment"])
        self.assertEqual({"Center", "CenterHorizontally", "End", "Top"}, set(alignment))

    def test_an_object_shadowed_by_a_function_of_its_name_is_left_out(self):
        """At run time `TextStyle` reaches the function, so `TextStyle.Default` is not there to stub."""
        notes: list[str] = []
        stubs = gen_stubs.generate(KOTLIN_STUBS_V2, PACKAGE, notes)
        self.assertNotIn("TextStyle", _classes(stubs[TEXT]))
        self.assertEqual(["font_size"], _parameter_names(_functions(stubs[TEXT])["TextStyle"][0]))
        self.assertNotIn("Default", _code_names(stubs[TEXT]))
        self.assertEqual(
            ["androidx.compose.ui.text.TextStyle"], [note.split(":")[0] for note in notes if "shadowed" in note]
        )

    def test_no_stub_lands_where_it_would_make_a_namespace_package(self):
        """A directory holding only `__init__.pyi` imports as a namespace package and would shadow
        the `KotlinObject` the re-export rule serves for that name."""
        for path in self.stubs:
            with self.subTest(stub=str(path.relative_to(REPO))):
                self.assertTrue((path.parent / "__init__.py").is_file())

    def test_a_second_module_for_the_same_package_re_exports_the_first(self):
        self.assertEqual(["from pythonx.compose.layout import *"], _imports(self.stubs[LONG_LAYOUT]))

    def test_aliases_are_re_exported(self):
        imports = _imports(self.stubs[MATERIAL3])
        for name in ("Column", "Row", "Spacer"):
            self.assertIn(f"from pythonx.compose.layout import {name} as {name}", imports)

    def test_a_renamed_path_alias_is_the_same_path_in_the_owners_stub(self):
        # `DefaultIcons` is `Icons.Default` of the icons module: not an import of that name (it
        # differs), but the same expression, so a checker reads what the icons stub says it is.
        text = self.stubs[MATERIAL3]
        self.assertIn("import pythonx.compose.material.icons as _alias_0", text)
        assigned = {
            n.targets[0].id: ast.unparse(n.value)
            for n in gen_stubs.parse(text).body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        }
        self.assertEqual("_alias_0.Icons.Default", assigned.get("DefaultIcons"))
        self.assertNotIn("DefaultIcons as", text)

    def test_a_constant_named_like_a_python_keyword_is_left_out(self):
        source = (
            "import typing as _t\n\nNone: _t.Any\n\"\"\"Kotlin: a.B.None(): a.B\"\"\"\n\n"
            "Hairline: float\n\"\"\"Kotlin: a.B.Hairline(): a.B\"\"\"\n"
        )
        tree = gen_stubs.parse(source)
        self.assertEqual(["Hairline"], [n.target.id for n in tree.body if isinstance(n, ast.AnnAssign)])

    def test_a_zip_converts_like_the_directory_and_tolerates_case_colliding_paths(self):
        (REPO / ".tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=REPO / ".tmp") as scratch:
            archive = Path(scratch) / "kotlin-stubs.zip"
            with zipfile.ZipFile(archive, "w") as out:
                for path in sorted(KOTLIN_STUBS_V2.rglob("*.pyi")):
                    out.write(path, path.relative_to(KOTLIN_STUBS_V2).as_posix())
                # The real artefact holds both: a package and an object differing only in case.
                out.writestr("androidx/compose/ui/text/shadow/__init__.pyi", "import typing as _t\n")
                out.writestr("androidx/compose/ui/text/Shadow/__init__.pyi", "import typing as _t\n\nNone: _t.Any\n")
            from_zip = _generated(archive)
        from_directory = _generated(KOTLIN_STUBS_V2)
        self.assertEqual(sorted(from_directory), sorted(from_zip))
        for path, text in from_directory.items():
            if path == TEXT:
                continue
            with self.subTest(stub=str(path.relative_to(REPO))):
                # Line 1 names the input, which differs; everything after it is the conversion.
                self.assertEqual(text.splitlines()[1:], from_zip[path].splitlines()[1:])
        self.assertIn("Shadow", _classes(from_zip[TEXT]))

    def test_every_stub_is_valid_python(self):
        for path, text in self.stubs.items():
            with self.subTest(stub=str(path.relative_to(REPO))):
                compile(text, str(path), "exec")


def _nested(cls: ast.ClassDef) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in cls.body if isinstance(node, ast.ClassDef)}


def _constants(cls: ast.ClassDef) -> set[str]:
    return {n.target.id for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}


class TheConstantGroups(unittest.TestCase):
    """SPEC S7.1: an object's constants grouped by the nested type their docstring declares."""

    OBJECT_IN_PARENT = (
        "import typing as _t\n\n"
        "class Obj:\n"
        "    \"\"\"Kotlin: a.b.Obj\"\"\"\n"
        "    Left: _t.ClassVar[_t.Any]\n"
        "    \"\"\"Kotlin: a.b.Obj.Left(): a.b.Obj.Side\"\"\"\n"
        "    Right: _t.ClassVar[_t.Any]\n"
        "    \"\"\"Kotlin: a.b.Obj.Right(): a.b.Obj.Side\"\"\"\n"
        "    Whole: _t.ClassVar[_t.Any]\n"
        "    \"\"\"Kotlin: a.b.Obj.Whole(): a.b.Obj\"\"\"\n"
        "    Deep: _t.ClassVar[_t.Any]\n"
        "    \"\"\"Kotlin: a.b.Obj.Deep(): a.b.Obj.Side.Inner\"\"\"\n"
        "    Other: _t.ClassVar[_t.Any]\n"
        "    \"\"\"Kotlin: a.b.Obj.Other(): a.c.Side\"\"\"\n"
    )

    def setUp(self):
        self.stubs = _generated(KOTLIN_STUBS_V2)

    def convert(self, source: str) -> dict[str, ast.ClassDef]:
        return _classes(gen_stubs.Converter(gen_stubs.KotlinStubs(KOTLIN_STUBS_V2)).convert(source, "a.b"))

    def test_constants_are_grouped_by_their_declared_nested_type(self):
        arrangement = _classes(self.stubs[LAYOUT])["Arrangement"]
        groups = _nested(arrangement)
        self.assertEqual(["Horizontal", "HorizontalOrVertical", "Vertical"], sorted(groups))
        self.assertEqual({"End", "Start"}, _constants(groups["Horizontal"]))
        self.assertEqual({"Top"}, _constants(groups["Vertical"]))
        self.assertEqual({"SpaceBetween"}, _constants(groups["HorizontalOrVertical"]))
        self.assertEqual(
            "_t.ClassVar[_t.Any]", ast.unparse(_members(groups["Horizontal"])["End"].annotation)
        )

    def test_the_flat_constants_stay(self):
        arrangement = _members(_classes(self.stubs[LAYOUT])["Arrangement"])
        self.assertTrue({"End", "Start", "Top", "SpaceBetween", "spaced_by"} <= set(arrangement))

    def test_an_object_class_in_the_parent_stub_is_grouped_too(self):
        obj = self.convert(self.OBJECT_IN_PARENT)["Obj"]
        self.assertEqual(["Side"], sorted(_nested(obj)))
        self.assertEqual({"Left", "Right"}, _constants(_nested(obj)["Side"]))
        self.assertEqual({"Left", "Right", "Whole", "Deep", "Other"}, _constants(obj))

    def test_a_member_named_like_the_type_wins(self):
        source = self.OBJECT_IN_PARENT + (
            "    Side: _t.ClassVar[_t.Any]\n"
            "    \"\"\"Kotlin: a.b.Obj.Side(): a.b.Obj.Side\"\"\"\n"
        )
        obj = self.convert(source)["Obj"]
        self.assertEqual({}, _nested(obj))
        self.assertIn("Side", _constants(obj))

    def test_a_class_with_no_such_constants_gets_no_groups(self):
        for name, cls in _classes(self.stubs[UI]).items():
            with self.subTest(cls=name):
                self.assertEqual({}, _nested(cls))


class TheObjectAndPropertyFormat(unittest.TestCase):
    """The upstream format of python-multiplatform #53 (objects), #38 (properties) and #44."""

    def setUp(self):
        self.stubs = _generated(KOTLIN_STUBS_V3)
        self.alignment = _classes(self.stubs[UI])["Alignment"]
        self.arrangement = _classes(self.stubs[LAYOUT])["Arrangement"]

    def test_a_property_and_its_setter_are_renamed_together(self):
        scene = _classes(self.stubs[UI])["Scene"]
        functions = [n for n in scene.body if isinstance(n, ast.FunctionDef)]
        self.assertEqual(["layout_direction", "layout_direction", "is_minimized", "is_minimized"],
                         [f.name for f in functions])
        self.assertEqual(
            [["property"], ["layout_direction.setter"], ["property"], ["is_minimized.setter"]],
            [[ast.unparse(d) for d in f.decorator_list] for f in functions],
        )

    def test_an_objects_nested_types_become_the_constant_groups(self):
        """The nested class is the Kotlin type and the notebook's group at once."""
        nested = _nested(self.alignment)
        self.assertEqual(["Horizontal", "Vertical"], sorted(nested))
        self.assertEqual({"End"}, _constants(nested["Horizontal"]))
        self.assertEqual({"Top"}, _constants(nested["Vertical"]))
        self.assertIn("Kotlin: androidx.compose.ui.Alignment.Horizontal", ast.get_docstring(nested["Horizontal"]))

    def test_a_constant_is_typed_with_its_nested_type_qualified(self):
        for cls, name, annotation in (
            (self.alignment, "End", "_t.ClassVar[Alignment.Horizontal]"),
            (self.alignment, "Center", "_t.ClassVar[_t.Any]"),
            (_nested(self.alignment)["Horizontal"], "End", "_t.ClassVar[Alignment.Horizontal]"),
            (self.arrangement, "End", "_t.ClassVar[Arrangement.Horizontal]"),
            # Derived from another nested type upstream, though Kotlin's is also a Vertical: Any.
            (self.arrangement, "SpaceBetween", "_t.ClassVar[_t.Any]"),
            (_nested(self.arrangement)["HorizontalOrVertical"], "SpaceBetween", "_t.ClassVar[_t.Any]"),
        ):
            with self.subTest(constant=name, annotation=annotation):
                self.assertEqual(annotation, ast.unparse(_members(cls)[name].annotation))

    def test_a_nested_types_base_is_qualified_too(self):
        bases = _nested(self.arrangement)["HorizontalOrVertical"].bases
        self.assertEqual(["Arrangement.Horizontal"], [ast.unparse(b) for b in bases])

    def test_a_reference_to_an_objects_nested_type_names_the_pythonx_module(self):
        column = _functions(self.stubs[LAYOUT])["Column"][0]
        self.assertEqual(
            ["pythonx.compose.ui.Alignment.Vertical", "pythonx.compose.ui.Alignment.Horizontal"],
            [ast.unparse(a.annotation) for a in column.args.args],
        )
        aligned = _members(self.arrangement)["aligned__Horizontal"]
        self.assertEqual("pythonx.compose.ui.Alignment.Horizontal", ast.unparse(aligned.args.args[0].annotation))
        self.assertEqual("Arrangement.Horizontal", ast.unparse(aligned.returns))

    def test_an_object_function_is_a_snake_case_static_method(self):
        members = self.arrangement.body
        spaced = [n for n in members if isinstance(n, ast.FunctionDef) and n.name.startswith("spaced_by")]
        self.assertEqual(["spaced_by", "spaced_by__Dp"], sorted(f.name for f in spaced))
        for function in spaced:
            self.assertIn("staticmethod", [ast.unparse(d) for d in function.decorator_list])
            self.assertEqual("_t.Any", ast.unparse(function.returns))

    def test_an_object_functions_overload_set_gets_its_base_name(self):
        aligned = [n for n in self.arrangement.body if isinstance(n, ast.FunctionDef) and n.name == "aligned"]
        self.assertEqual(2, len(aligned))
        for function in aligned:
            self.assertEqual(["staticmethod", "_t.overload"], [ast.unparse(d) for d in function.decorator_list])


class TheMultiBaseAndIconFormat(unittest.TestCase):
    """python-multiplatform #71 (a nested type lists every base) and #68 (icons are typed properties)."""

    def setUp(self):
        self.stubs = _generated(KOTLIN_STUBS_V4)
        self.arrangement = _classes(self.stubs[LAYOUT])["Arrangement"]

    def test_a_nested_type_with_two_bases_is_trusted_and_names_both(self):
        both = _nested(self.arrangement)["HorizontalOrVertical"]
        self.assertEqual(["Arrangement.Horizontal", "Arrangement.Vertical"], [ast.unparse(b) for b in both.bases])
        for cls, name in ((self.arrangement, "SpaceBetween"), (both, "SpaceBetween")):
            self.assertEqual(
                "_t.ClassVar[Arrangement.HorizontalOrVertical]", ast.unparse(_members(cls)[name].annotation)
            )
        spaced = [n for n in self.arrangement.body if isinstance(n, ast.FunctionDef) and n.name == "spaced_by"]
        self.assertEqual("Arrangement.HorizontalOrVertical", ast.unparse(spaced[0].returns))

    def test_a_nested_type_with_one_base_is_still_any(self):
        """The old input cannot say it is also a `Vertical`: nothing is claimed (the v3 fixture)."""
        arrangement = _classes(_generated(KOTLIN_STUBS_V3)[LAYOUT])["Arrangement"]
        self.assertEqual("_t.ClassVar[_t.Any]", ast.unparse(_members(arrangement)["SpaceBetween"].annotation))

    def test_a_single_sided_constant_keeps_its_one_type(self):
        self.assertEqual("_t.ClassVar[Arrangement.Horizontal]", ast.unparse(_members(self.arrangement)["End"].annotation))

    def test_an_icon_is_a_property_typed_as_an_image_vector(self):
        icons = _classes(self.stubs[ICONS])["Icons"]
        add = _members(_nested(icons)["Filled"])["Add"]
        self.assertEqual(["property"], [ast.unparse(d) for d in add.decorator_list])
        self.assertEqual("pythonx.compose.ui.graphics.vector.ImageVector", ast.unparse(add.returns))
        self.assertIn("import pythonx.compose.ui.graphics.vector", _imports(self.stubs[ICONS]))

    def test_a_nested_container_keeps_its_icons_with_the_kotlin_spelling(self):
        mirrored = _nested(_nested(_classes(self.stubs[ICONS])["Icons"])["AutoMirrored"])["Filled"]
        self.assertEqual({"ArrowBack"}, set(_members(mirrored)))
        self.assertEqual("_t.ClassVar[Icons.Filled]", ast.unparse(_members(_classes(self.stubs[ICONS])["Icons"])["Default"].annotation))


class TheConstructorShapedFunction(unittest.TestCase):
    """A class and an explicit overload set of its name (`DpRect__Dp_Dp_Dp_Dp`) in one stub."""

    SOURCE = (
        "import typing as _t\n\n"
        "class Rect:\n"
        "    def __init__(self, left: float, top: float) -> None: ...\n\n"
        "def Rect__Dp_Dp(left: float, top: float) -> Rect: ...\n"
        "def Spot__Dp(left: float) -> float: ...\n"
    )

    def test_the_class_keeps_its_name_and_the_function_gets_no_base_name(self):
        text = gen_stubs.Converter(gen_stubs.KotlinStubs(KOTLIN_STUBS_V4)).convert(self.SOURCE, "a.b")
        self.assertEqual(["Rect"], list(_classes(text)))
        self.assertEqual(["Rect__Dp_Dp", "Spot__Dp", "Spot"], list(_functions(text)))
        ast.parse(text)


class TheCommittedStubs(unittest.TestCase):
    """What ships is what the generator makes of python-multiplatform's `kotlin-stubs` artefact."""

    def test_py_typed_and_a_stub_for_every_mapped_module_are_committed(self):
        self.assertTrue((COMPOSE / "py.typed").is_file())
        for module_name in gen_stubs.manifest()["modules"]:
            with self.subTest(module=module_name):
                self.assertTrue((PACKAGE.joinpath(*module_name.split(".")[1:]) / "__init__.pyi").is_file())

    def test_the_committed_stubs_are_exactly_what_the_artefact_generates(self):
        if not ARTEFACT.is_file():
            self.skipTest(
                f"{ARTEFACT.relative_to(REPO)} is absent: download python-multiplatform's `kotlin-stubs` "
                "artefact there to check the committed stubs against it"
            )
        generated = gen_stubs.generate(ARTEFACT, PACKAGE)
        committed = {
            path for path in COMPOSE.rglob("*.pyi")
            if "lite" not in path.relative_to(COMPOSE).parts
        }
        self.assertEqual(sorted(committed), sorted(generated))
        for path, text in generated.items():
            with self.subTest(stub=str(path.relative_to(REPO))):
                self.assertEqual(text, path.read_text(encoding="utf-8"))

    def test_the_committed_icons_stub_declares_icons_and_material3_declares_default_icons(self):
        icons = ICONS.read_text(encoding="utf-8")
        self.assertIn("Icons", _classes(icons))
        self.assertIn("DefaultIcons = _alias_0.Icons.Default", MATERIAL3.read_text(encoding="utf-8"))

    def test_the_committed_alignment_and_arrangement_carry_their_groups(self):
        alignment = _nested(_classes(UI.read_text(encoding="utf-8"))["Alignment"])
        self.assertEqual({"CenterHorizontally", "End", "Start"}, _constants(alignment["Horizontal"]))
        self.assertEqual({"Bottom", "CenterVertically", "Top"}, _constants(alignment["Vertical"]))
        arrangement = _nested(_classes(LAYOUT.read_text(encoding="utf-8"))["Arrangement"])
        self.assertEqual(
            {"Center", "SpaceAround", "SpaceBetween", "SpaceEvenly"}, _constants(arrangement["HorizontalOrVertical"])
        )


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
        import pythonx.compose.layout as layout

        functions = _functions(_generated()[LAYOUT])
        for name in ("padding__Dp", "padding__Dp_Dp", "padding__PaddingValues", "padding_values_of",
                     "size__Dp", "fill_max_width"):
            with self.subTest(name=name):
                runtime = list(inspect.signature(getattr(layout, name)).parameters)
                self.assertEqual(runtime, _parameter_names(functions[name][0]))

    def test_the_current_format_has_the_same_parameter_names(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        stubs = _generated(KOTLIN_STUBS_V2)
        functions = {**_functions(stubs[LAYOUT]), **_functions(stubs[UI])}
        for module, name in ((layout, "padding__Dp"), (layout, "padding__Dp_Dp"),
                             (layout, "padding__Dp_Dp_Dp_Dp"), (layout, "padding__PaddingValues"),
                             (layout, "padding_values_of"), (layout, "size__Dp"),
                             (layout, "fill_max_width"), (ui, "describe_modifier"), (ui, "to_url_string")):
            with self.subTest(name=name):
                runtime = list(inspect.signature(getattr(module, name)).parameters)
                self.assertEqual(runtime, _parameter_names(functions[name][0]))

    def test_an_object_function_has_the_same_parameter_names(self):
        import pythonx.compose.layout as layout

        arrangement = _members(_classes(_generated(KOTLIN_STUBS_V2)[LAYOUT])["Arrangement"])
        runtime = list(inspect.signature(layout.Arrangement.spaced_by).parameters)
        self.assertEqual(runtime, _parameter_names(arrangement["spaced_by"]))

    def test_an_object_constant_in_the_stub_is_read_at_run_time(self):
        import pythonx.compose.layout as layout
        import pythonx.compose.ui as ui

        stubs = _generated(KOTLIN_STUBS_V2)
        for module, stub, name in ((layout, LAYOUT, "Arrangement"), (ui, UI, "Alignment")):
            for constant in _members(_classes(stubs[stub])[name]):
                with self.subTest(constant=f"{name}.{constant}"):
                    self.assertIsNotNone(getattr(getattr(module, name), constant))

    def test_a_group_in_the_stub_holds_what_the_runtime_group_holds(self):
        import python_multiplatform
        import pythonx.compose.layout as layout

        if len(inspect.signature(python_multiplatform.describe).parameters) < 2:
            self.skipTest("the binder has no describe(module, name) yet (python-multiplatform #36)")
        groups = _nested(_classes(_generated(KOTLIN_STUBS_V2)[LAYOUT])["Arrangement"])
        self.assertTrue(groups)
        for name, group in groups.items():
            with self.subTest(group=name):
                self.assertEqual(sorted(_constants(group)), dir(getattr(layout.Arrangement, name)))


if __name__ == "__main__":
    unittest.main()
