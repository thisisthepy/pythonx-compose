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
  `Modifier.padding(16).fill_max_width()` reaches `fillMaxWidth` on a proxy Kotlin returned. The
  binder caches the alias in its own registry; its proxy classes keep Kotlin names in `dir()`.

Nothing here names a Kotlin declaration. Names defined in the package's own `__init__.py` (such as
`runtime.Composable`) are ordinary module attributes and win, because `__getattr__` only runs for a
name the module does not already have.
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
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


def member_name(kotlin_type_name: str, requested: str, kotlin_member_names) -> str | None:
    """The binder's member-resolver hook: the Kotlin member a Pythonic name means on a proxy.

    The binder asks this only for a name its proxy has no Kotlin member of
    (`python_multiplatform.binding.add_member_resolver`). The rule is the module rule, applied
    forward to the proxy's real member names: `fill_max_width` finds `fillMaxWidth`.
    """
    matches = [name for name in kotlin_member_names if python_name(name) == requested]
    return matches[0] if len(matches) == 1 else None


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
    if isinstance(value, type) or not callable(value):
        return value
    return PythonicFunction(value, name)


def reexport(module_name: str):
    """The module-level `__getattr__` and `__dir__` for the mapped package `module_name`.

    Nothing is resolved here, only when a name is first read, so importing a `pythonx.compose`
    module needs neither the manifest row's Kotlin package nor an installed binder.
    """

    def __getattr__(name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        kotlin = kotlin_module(module_name)
        kotlin_name = _name_table(kotlin).get(name)
        if kotlin_name is None:
            raise AttributeError(
                f"module {module_name!r} has no attribute {name!r} (nothing in Kotlin package "
                f"{kotlin.__name__} is spelled that way under pythonx's naming rule)"
            )
        value = getattr(kotlin, kotlin_name)
        if kotlin_name not in vars(kotlin):
            # The binder declined to cache it -- a live property, read again on every access -- so
            # this layer does not freeze it either.
            return value
        adapted = _pythonic(value, name)
        setattr(sys.modules[module_name], name, adapted)
        return adapted

    def __dir__():
        own = set(vars(sys.modules[module_name]))
        try:
            own.update(_name_table(kotlin_module(module_name)))
        except (RuntimeError, ImportError):
            pass
        return sorted(own)

    return __getattr__, __dir__
