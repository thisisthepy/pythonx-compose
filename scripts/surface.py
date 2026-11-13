"""The public surface of a generated `pythonx.compose` stub, for the regression guard (#152, #54).

    python3 scripts/surface.py pythonx.compose.material3 [more modules ...]

writes `tests/fixtures/surfaces/<module>.txt` from the committed stub of each module named. Run it
when a regenerated stub is reviewed and accepted; `tests/test_design_systems.py` then fails if a later
regeneration drops or changes a recorded line that `tests/fixtures/surfaces/allowlist.toml` does not
acknowledge.

A line is one declaration: a function or method with its parameter names (`=...` marks a default,
`/` and `*` keep their places) and return type, one line per overload; a class; an annotated name
with its type; a re-exported or aliased name. Parameter types are left out on purpose: the binder's
typing of a parameter improves over time (`_t.Any` becomes a class), and that is not a regression.
Return types stay, because a caller's chain depends on them.

Build tooling, not shipped in the wheel (AGENTS.md section 2).
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SURFACES = REPO / "tests" / "fixtures" / "surfaces"


def _parameters(arguments: ast.arguments) -> str:
    parts: list[str] = []
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults = [None] * (len(positional) - len(arguments.defaults)) + list(arguments.defaults)
    for index, (argument, default) in enumerate(zip(positional, defaults)):
        parts.append(argument.arg + ("=..." if default is not None else ""))
        if arguments.posonlyargs and index == len(arguments.posonlyargs) - 1:
            parts.append("/")
    if arguments.vararg is not None:
        parts.append("*" + arguments.vararg.arg)
    elif arguments.kwonlyargs:
        parts.append("*")
    for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults):
        parts.append(argument.arg + ("=..." if default is not None else ""))
    if arguments.kwarg is not None:
        parts.append("**" + arguments.kwarg.arg)
    return ", ".join(parts)


def _lines(body: list[ast.stmt], prefix: str) -> list[str]:
    found: list[str] = []
    for node in body:
        if isinstance(node, ast.FunctionDef):
            returns = ast.unparse(node.returns) if node.returns is not None else "_t.Any"
            found.append(f"{prefix}{node.name}({_parameters(node.args)}) -> {returns}")
        elif isinstance(node, ast.ClassDef):
            found.append(f"class {prefix}{node.name}")
            found.extend(_lines(node.body, f"{prefix}{node.name}."))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            found.append(f"{prefix}{node.target.id}: {ast.unparse(node.annotation)}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    found.append(f"{prefix}{target.id} = {ast.unparse(node.value).split('.', 1)[-1]}")
        elif isinstance(node, ast.ImportFrom) and not prefix:
            for alias in node.names:
                found.append(f"{alias.asname or alias.name} from {node.module}")
    return found


def surface(stub_text: str) -> list[str]:
    """Every public declaration line of [stub_text], sorted, without repeats."""
    tree = ast.parse(stub_text)
    return sorted({line for line in _lines(tree.body, "") if not line.split("(")[0].rsplit(".", 1)[-1].startswith("_")})


def read_snapshot(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]


def allowlist(path: Path) -> dict[str, set[str]]:
    """Module -> snapshot lines a reviewer has acknowledged as lost (`[[lost]]` module, line, reason)."""
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        entries = tomllib.load(handle).get("lost", [])
    allowed: dict[str, set[str]] = {}
    for entry in entries:
        allowed.setdefault(entry["module"], set()).add(entry["line"])
    return allowed


def lost(snapshot: list[str], current: list[str], allowed: set[str]) -> list[str]:
    """Snapshot lines that [current] no longer has and nobody acknowledged."""
    present = set(current)
    return [line for line in snapshot if line not in present and line not in allowed]


def _stub_path(module: str) -> Path:
    return REPO.joinpath(*module.split(".")) / "__init__.pyi"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    SURFACES.mkdir(parents=True, exist_ok=True)
    for module in argv:
        lines = surface(_stub_path(module).read_text(encoding="utf-8"))
        out = SURFACES / f"{module}.txt"
        head = f"# Public surface of {module}, recorded by scripts/surface.py from its committed stub.\n"
        out.write_text(head + "".join(line + "\n" for line in lines), encoding="utf-8")
        print(f"{out.relative_to(REPO)}: {len(lines)} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
