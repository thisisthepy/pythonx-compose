"""The one rule that makes a `pythonx.compose.*` module a Pythonic view of a Kotlin package.

The binder (`python-multiplatform`) serves every bound Kotlin package under its **Kotlin** name --
`androidx.compose.foundation.layout` -- with Kotlin's own surface: declaration names, keyword
arguments by Kotlin parameter name, Kotlin defaults, overload dispatch. It renames nothing, and it
publishes what a Pythonic layer needs to rename by rule: `inspect.signature(fn)` with the Kotlin
parameter names, and `python_multiplatform.describe(fn)` with one dict per overload.

This module is that layer. A mapped package's `__init__.py` is one line::

    __getattr__, __dir__ = reexport(__name__)

and every name in it then resolves against the Kotlin package `pythonx-map.toml` maps it to:

- **Names.** A name that starts upper-case -- a type, an object, a `@Composable` -- keeps its Kotlin
  spelling (`Modifier`, `Text`). Any other name is reached by its snake_case spelling only
  (`fillMaxWidth` -> `fill_max_width`, `toURLString` -> `to_url_string`), and an explicit overload
  keeps its suffix (`padding__Dp`). The inverse is never computed: the module's real Kotlin names
  are converted forward and looked up, so a name the reverse rule could not invert still resolves.
- **Keywords.** `on_click=` reaches the parameter Kotlin calls `onClick`, matched against the
  declaration's own parameter names (every overload's), never derived.
- **Signatures.** A re-exported function answers `inspect.signature` with the snake_case names;
  defaults stay `python_multiplatform.KOTLIN_DEFAULT`.
- **Value classes.** The manifest's `raw-primitive-allowed` list is handed to the binder once per
  installed binding layer, so `padding(16)` reaches a `Dp` parameter.
- **Methods on a proxy.** The same name rule is registered as the binder's member resolver, so
  `Modifier.padding(16).fill_max_width()` reaches `fillMaxWidth` on a proxy Kotlin returned, and
  `m.padding(padding_values=...)` reaches `paddingValues`: the resolver also answers a keyword map,
  read from `python_multiplatform.describe_member`. The Kotlin spelling still works. The binder
  caches the alias in its own registry; its proxy classes keep Kotlin names in `dir()`.

- **Grouped constants.** Inside a Kotlin object served as a namespace, a type nested in it that
  is not one of its members groups the constants declared as exactly that type, so the notebook's
  `Alignment.Horizontal.End` reads `Alignment.End` (`ConstantGroup`). Declared types come from
  `python_multiplatform.describe(module, name)`, which never runs a constant's getter.

A module may also answer for names the manifest's `[aliases]` section lends it from another mapped
module (`material3` answers for `Column`, `Row`, `Spacer` from `layout`, as the notebook imports
them); the object is the same one either way.

Nothing here names a Kotlin declaration. Names defined in the package's own `__init__.py` (such as
`runtime.Composable`) are ordinary module attributes and win, because `__getattr__` only runs for a
name the module does not already have.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import re
import sys
import types
import weakref
from functools import lru_cache
from pathlib import Path

ROOT_MODULE = "python_multiplatform"
BINDING_MODULE = "python_multiplatform.binding"

_MANIFEST = Path(__file__).resolve().parent / "pythonx-map.toml"

_LOWER_UPPER = re.compile(r"([a-z0-9])([A-Z])")
_ACRONYM_WORD = re.compile(r"([A-Z]+)([A-Z][a-z])")


def snake_case(kotlin_name: str) -> str:
    """`fillMaxWidth` -> `fill_max_width`, `toURLString` -> `to_url_string`, `zIndex` -> `z_index`."""
    return _LOWER_UPPER.sub(r"\1_\2", _ACRONYM_WORD.sub(r"\1_\2", kotlin_name)).lower()


def python_name(kotlin_name: str) -> str:
    """The one Pythonic spelling of a Kotlin declaration name.

    Upper-case names are types, objects and composables and keep their Kotlin spelling. An explicit
    overload (`padding__Dp`) converts its base and keeps the type suffix, which names Kotlin types.
    """
    if kotlin_name[:1].isupper():
        return kotlin_name
    base, sep, suffix = kotlin_name.partition("__")
    return snake_case(base) + sep + suffix


@lru_cache(maxsize=1)
def manifest() -> dict:
    """`pythonx-map.toml`, parsed once."""
    import tomllib

    with _MANIFEST.open("rb") as handle:
        return tomllib.load(handle)


def kotlin_package_of(module_name: str) -> str:
    try:
        return manifest()["modules"][module_name]
    except KeyError:
        raise LookupError(
            f"{module_name} has no row in pythonx-map.toml; a re-exported module needs one"
        ) from None


def binding_layer():
    """The binder's installed binding module, or a `RuntimeError` that says what did not happen."""
    binding = sys.modules.get(BINDING_MODULE)
    if binding is None:
        raise RuntimeError(
            "the python-multiplatform binding layer is not installed: the Kotlin host must run "
            "PythonxAdapter.install() before pythonx.compose can resolve a Kotlin declaration"
        )
    return binding


_PRIMED = weakref.WeakSet()


_MEMBER_KEYWORDS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _method_keywords(kotlin_type_name: str, kotlin_member_name: str) -> dict:
    """`{snake_case(p): p}` for every parameter `p` of every declaration of a proxy's member.

    Read with `python_multiplatform.describe_member`, which lists each overload's parameters without
    invoking anything (the receiver slot is not among them). It is metadata, so it is kept per
    (type, member), under the `describe_member` of the binding layer that answered: a new layer
    starts with an empty table. A keyword whose snake_case spelling is its own is left out, and a
    binder without `describe_member`, or a member it does not describe, has no map.
    """
    describe_member = getattr(sys.modules.get(ROOT_MODULE), "describe_member", None)
    if describe_member is None:
        return {}
    try:
        known = _MEMBER_KEYWORDS.setdefault(describe_member, {})
    except TypeError:  # something that cannot be weakly referenced: nothing to key a cache by
        known = {}
    key = (kotlin_type_name, kotlin_member_name)
    if key not in known:
        keywords: dict = {}
        try:
            declarations = describe_member(kotlin_type_name, kotlin_member_name)
        except (TypeError, AttributeError):
            declarations = ()
        for declaration in declarations:
            for parameter in declaration.get("parameters", ()):
                kotlin_parameter = parameter.get("name")
                if kotlin_parameter and snake_case(kotlin_parameter) != kotlin_parameter:
                    keywords.setdefault(snake_case(kotlin_parameter), kotlin_parameter)
        known[key] = keywords
    return known[key]


def member_name(kotlin_type_name: str, requested: str, kotlin_member_names):
    """The binder's member-resolver hook: the Kotlin member a Pythonic name means on a proxy, and
    the keywords it takes.

    The binder asks for a name its proxy has no Kotlin member of
    (`python_multiplatform.binding.add_member_resolver`): the rule is the module rule applied
    forward to the proxy's real member names, so `fill_max_width` finds `fillMaxWidth`. It asks
    again for a Kotlin member name when a call passes keywords. The answer is then
    `(kotlin_name, {python_keyword: kotlinParameter})`, the parameters of every overload of that
    member, so `m.padding(padding_values=...)` reaches `paddingValues`. Without a keyword to map the
    answer is the name alone, which is all a binder without `describe_member` can be given.
    """
    if requested in kotlin_member_names:
        target = requested
    else:
        matches = [name for name in kotlin_member_names if python_name(name) == requested]
        target = matches[0] if len(matches) == 1 else None
    if target is None:
        return None
    keywords = _method_keywords(kotlin_type_name, target)
    return (target, keywords) if keywords else target


def _prime(binding) -> None:
    """Hand this binding layer the manifest's value-class allowlist and the member rule, once.

    The member rule needs python-multiplatform's `add_member_resolver`; on a binder without it,
    methods on a returned proxy stay reachable by their Kotlin names only.
    """
    if binding in _PRIMED:
        return
    for kotlin_type in manifest().get("value-classes", {}).get("raw-primitive-allowed", ()):
        binding.allow_raw_primitive(kotlin_type)
    add_member_resolver = getattr(binding, "add_member_resolver", None)
    if add_member_resolver is not None:
        add_member_resolver(member_name)
    _PRIMED.add(binding)


def kotlin_module(module_name: str):
    """The binder's module for the Kotlin package `module_name` maps to."""
    _prime(binding_layer())
    return importlib.import_module(kotlin_package_of(module_name))


def _name_table(kotlin) -> dict:
    """Pythonic name -> Kotlin name for everything the Kotlin module reports, with collisions refused."""
    table = {}
    for kotlin_name in dir(kotlin):
        if kotlin_name.startswith("_"):
            continue
        pythonic = python_name(kotlin_name)
        other = table.get(pythonic)
        if other is not None and other != kotlin_name:
            raise AttributeError(
                f"{pythonic!r} would name both {other!r} and {kotlin_name!r} in {kotlin.__name__}; "
                "reach one by its explicit overload spelling"
            )
        table[pythonic] = kotlin_name
    return table


def _declared_type(kotlin, kotlin_name: str):
    """`(kind, declared return type)` of the bound name [kotlin_name] in [kotlin], without reading it.

    `python_multiplatform.describe(module, name)` answers from the binder's table and never runs a
    constant's getter (python-multiplatform #36). A binder without the two-argument form, or a name
    that is not a single bound declaration (an overload set, a child package), answers `None`.
    """
    root = sys.modules.get(ROOT_MODULE)
    describe = getattr(root, "describe", None)
    if describe is None:
        return None
    try:
        described = describe(kotlin, kotlin_name)
    except (TypeError, AttributeError):
        return None
    if not isinstance(described, dict):
        return None
    return described.get("kind"), described.get("returns")


def _describe(fn):
    root = sys.modules.get(ROOT_MODULE)
    if root is None or not hasattr(root, "describe"):
        return ()
    try:
        return root.describe(fn)
    except (TypeError, AttributeError):
        return ()


class PythonicFunction:
    """A binder callable seen through the naming rule: snake_case keywords and signature.

    Calls go straight to the binder's callable with the keywords translated; overload selection,
    defaults and value classes are the binder's. A keyword that matches no parameter is passed on
    unchanged, so the binder's own refusal -- which lists the candidates -- is what the caller sees.
    """

    __slots__ = ("_kotlin", "_keywords", "__name__", "__qualname__")

    def __init__(self, kotlin_fn, name):
        self._kotlin = kotlin_fn
        self.__name__ = name
        self.__qualname__ = name
        keywords = {}
        for row in _describe(kotlin_fn):
            for parameter in row.get("parameters", ()):
                kotlin_parameter = parameter["name"]
                keywords.setdefault(snake_case(kotlin_parameter), kotlin_parameter)
        self._keywords = keywords

    @property
    def __kotlin__(self):
        """The binder's callable this wraps."""
        return self._kotlin

    @property
    def __kotlin_rows__(self):
        return self._kotlin.__kotlin_rows__

    @property
    def __signature__(self):
        kotlin_signature = inspect.signature(self._kotlin)
        return kotlin_signature.replace(parameters=[
            parameter if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD)
            else parameter.replace(name=snake_case(parameter.name))
            for parameter in kotlin_signature.parameters.values()
        ])

    def __call__(self, *args, **kwargs):
        if kwargs:
            kwargs = {self._keywords.get(key, key): value for key, value in kwargs.items()}
        return self._kotlin(*args, **kwargs)

    def __repr__(self):
        return f"<pythonx function {self.__name__} -> {self._kotlin!r}>"


def _pythonic(value, name):
    if isinstance(value, types.ModuleType):
        # A Kotlin object served as a sub-package. Since python-multiplatform #35 the binder lists it
        # and exposes it as an attribute of its parent, so the name table reaches it directly.
        return KotlinObject(value)
    if isinstance(value, type) or not callable(value):
        return value
    return PythonicFunction(value, name)


def _resolve(kotlin, name: str):
    """What the Pythonic [name] means in the binder's module [kotlin]: `(value, cacheable)` or `None`.

    A name the module lists is looked up by the rule. An upper-case name it does not list may be a
    Kotlin object served as a sub-package (`androidx.compose.ui.Alignment`), which the binder imports
    on demand but does not list or expose as an attribute before that (python-multiplatform #35);
    it comes back as a `KotlinObject` namespace read by the same rule.
    """
    kotlin_name = _name_table(kotlin).get(name)
    if kotlin_name is not None:
        value = getattr(kotlin, kotlin_name)
        # The binder declined to cache it -- a live property, read again on every access -- so this
        # layer does not freeze it either.
        return _pythonic(value, name), kotlin_name in vars(kotlin)
    if name[:1].isupper():
        try:
            nested = importlib.import_module(kotlin.__name__ + "." + name)
        except ImportError:
            return None
        return KotlinObject(nested), True
    return None


_STATIC_GETTER = "STATIC_GETTER"


def _constant_groups(kotlin) -> dict:
    """Group name -> {Pythonic constant name: Kotlin name}, for the Kotlin object [kotlin].

    A group is a type nested in the object, `P.G`, that some constant of `P` is declared as; it holds
    exactly the constants declared as `P.G` (SPEC S7.1). A constant declared as `P` itself or as any
    other type is in no group. Declared types come from `describe(module, name)`, never from a value.
    A name the object already has is a Kotlin member and wins, so it is never a group.
    """
    prefix = kotlin.__name__ + "."
    members = _name_table(kotlin)
    groups: dict = {}
    for pythonic, kotlin_name in members.items():
        declared = _declared_type(kotlin, kotlin_name)
        if declared is None or declared[0] != _STATIC_GETTER or not declared[1]:
            continue
        group = declared[1][len(prefix):] if declared[1].startswith(prefix) else ""
        if not group[:1].isupper() or "." in group or group in members:
            continue
        groups.setdefault(group, {})[pythonic] = kotlin_name
    return groups


class KotlinObject:
    """A Kotlin object (`Arrangement`, `Alignment`) served as a namespace, read by the module rule.

    Constants are read again on every access, as the binder serves them; functions inside the object
    are snake_case (`Arrangement.spaced_by`) and are resolved once. A type nested in the object that
    is no member of it groups the constants declared as that type (`Alignment.Horizontal.End`,
    `ConstantGroup`); which constants those are is worked out once per object, from declared types.
    """

    __slots__ = ("_kotlin", "_cache", "_groups")

    def __init__(self, kotlin_module):
        object.__setattr__(self, "_kotlin", kotlin_module)
        object.__setattr__(self, "_cache", {})
        object.__setattr__(self, "_groups", None)

    def _constant_groups(self) -> dict:
        if self._groups is None:
            object.__setattr__(self, "_groups", _constant_groups(self._kotlin))
        return self._groups

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        cached = self._cache.get(name)
        if cached is not None:
            return cached
        resolved = _resolve(self._kotlin, name)
        if resolved is None:
            members = self._constant_groups().get(name) if name[:1].isupper() else None
            if members is None:
                raise AttributeError(
                    f"{self._kotlin.__name__} has nothing spelled {name!r} under pythonx's naming rule"
                )
            # The grouping is metadata and is kept; the constants inside are read on each access.
            resolved = ConstantGroup(self, f"{self._kotlin.__name__}.{name}", members), True
        value, cacheable = resolved
        if cacheable:
            self._cache[name] = value
        return value

    def __setattr__(self, name, value):
        raise AttributeError(f"{self._kotlin.__name__} is a Kotlin object; its members are read-only here")

    def __dir__(self):
        return sorted(set(_name_table(self._kotlin)) | set(self._constant_groups()))

    def __repr__(self):
        return f"<pythonx view of Kotlin object {self._kotlin.__name__}>"


class ConstantGroup:
    """The constants of a Kotlin object declared as one type nested in it: `Alignment.Horizontal`.

    The notebook's grouped spelling (INTENT section 5.3). Reading `Alignment.Horizontal.End` reads
    `Alignment.End` through its `KotlinObject`, so both spellings are the same live read of the same
    Kotlin getter. Only constants whose *declared* type is exactly this one are here.
    """

    __slots__ = ("_owner", "_kotlin_type", "_members")

    def __init__(self, owner, kotlin_type, members):
        object.__setattr__(self, "_owner", owner)
        object.__setattr__(self, "_kotlin_type", kotlin_type)
        object.__setattr__(self, "_members", dict(members))

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if name not in self._members:
            raise AttributeError(
                f"{self._kotlin_type} groups no constant spelled {name!r}; it holds the constants of "
                f"{self._owner._kotlin.__name__} declared as {self._kotlin_type}: "
                + ", ".join(sorted(self._members))
            )
        return getattr(self._owner, name)

    def __setattr__(self, name, value):
        raise AttributeError(f"{self._kotlin_type} is a group of Kotlin constants; they are read-only here")

    def __dir__(self):
        return sorted(self._members)

    def __repr__(self):
        return f"<pythonx group of {self._owner._kotlin.__name__} constants declared {self._kotlin_type}>"


def _aliases(module_name: str) -> dict:
    """Name -> the `pythonx.compose` module it is borrowed from, per the manifest's `[aliases]`."""
    borrowed = {}
    for source, names in manifest().get("aliases", {}).get(module_name, {}).items():
        for name in names:
            borrowed[name] = source
    return borrowed


def reexport(module_name: str):
    """The module-level `__getattr__` and `__dir__` for the mapped package `module_name`.

    Nothing is resolved here, only when a name is first read, so importing a `pythonx.compose`
    module needs neither the manifest row's Kotlin package nor an installed binder.
    """

    def __getattr__(name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        if importlib.util.find_spec(module_name + "." + name) is not None:
            # A submodule file of this package (`ui.modifier`). `from package import name` asks for
            # the attribute before it imports a submodule, and only an AttributeError lets it
            # fall back -- so this has to answer before anything that needs the binder.
            return importlib.import_module(module_name + "." + name)
        source = _aliases(module_name).get(name)
        if source is not None:
            value = getattr(importlib.import_module(source), name)
            setattr(sys.modules[module_name], name, value)
            return value
        try:
            kotlin = kotlin_module(module_name)
        except ImportError as missing:
            raise AttributeError(
                f"module {module_name!r} has no attribute {name!r} ({missing})"
            ) from missing
        resolved = _resolve(kotlin, name)
        if resolved is None:
            raise AttributeError(
                f"module {module_name!r} has no attribute {name!r} (nothing in Kotlin package "
                f"{kotlin.__name__} is spelled that way under pythonx's naming rule)"
            )
        value, cacheable = resolved
        if cacheable:
            setattr(sys.modules[module_name], name, value)
        return value

    def __dir__():
        own = set(vars(sys.modules[module_name])) | set(_aliases(module_name))
        try:
            own.update(_name_table(kotlin_module(module_name)))
        except (RuntimeError, ImportError):
            pass
        return sorted(own)

    return __getattr__, __dir__
