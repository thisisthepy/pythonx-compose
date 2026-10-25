"""TypedPython's soundness gate passes on this package's own Python (issue #118).

python-multiplatform's `typedpython check` runs Pyrefly over `pythonx/` and reports, as errors, every
Pyrefly error and every expression of type `Any` outside a `cast()` (`any-flow`), and, as warnings
in `checked` mode, the dynamic features on its forbidden list. toolchain's `typedpythonCheck` runs the
same gate in the build, so an error here would fail the build of an app that checks this package.

The repository root is the gate's search path, so `pythonx.compose._reexport` resolves as the
installed package does. No Kotlin stub is on it: what this package reads from the binder is typed
here as an opaque `object` or module, not taken from `androidx` stubs.

What stays is five `forbidden/dynamic-attr` warnings, and they are the re-export layer itself: a name
read at run time is forwarded to the binder's module (`_resolve`), an alias's attribute path from
`pythonx-map.toml` is walked (`_borrow`, twice), and a resolved value is kept on the module that
answered for it (`_borrow`, `reexport`). Hiding them behind a `__dict__` lookup would only hide them
from the gate (AGENTS.md section 13).

Needs a python-multiplatform checkout (`PYTHONMULTIPLATFORM_HOME`, or the sibling directory) for
the gate's source, and `pyrefly` 1.3.2 importable in the running interpreter; without either the
tests skip, saying which, and a skip is not a pass.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapter import python_multiplatform_home  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
GATE_SOURCE = Path("python-multiplatform-ksp/src/main/python")

KEPT_DYNAMIC_ATTRIBUTES = 5
"""`_resolve` 1, `_borrow` 3, `reexport` 1: see the module docstring."""


def _run_gate(gate_root: Path) -> list[dict]:
    env = {**os.environ, "PYTHONPATH": str(gate_root), "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [sys.executable, "-m", "typedpython", "check", "--format", "json",
         "--search-path", str(REPO), str(REPO / "pythonx")],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    if done.returncode not in (0, 1):
        raise AssertionError(f"the gate could not run (exit {done.returncode}):\n{done.stderr}")
    return json.loads(done.stdout)


def _show(found: list[dict]) -> str:
    return "\n".join(
        f"{d['severity']} {Path(d['path']).relative_to(REPO)}:{d['line']}: {d['message']} [{d['rule']}]"
        for d in found
    )


class TheGate(unittest.TestCase):

    found: list[dict]

    @classmethod
    def setUpClass(cls):
        gate_root = python_multiplatform_home() / GATE_SOURCE
        if not (gate_root / "typedpython" / "gate.py").is_file():
            raise unittest.SkipTest(f"no TypedPython gate at {gate_root} (a python-multiplatform checkout)")
        if importlib.util.find_spec("pyrefly") is None:
            raise unittest.SkipTest("pyrefly is not importable; the gate runs it as `python -m pyrefly`")
        cls.found = _run_gate(gate_root)

    def of(self, severity: str) -> list[dict]:
        return [d for d in self.found if d["severity"] == severity]

    def test_every_function_is_annotated(self):
        missing = [d for d in self.found
                   if d["rule"] in ("pyrefly/unannotated-return", "pyrefly/implicit-any-parameter")]
        self.assertEqual([], missing, _show(missing))

    def test_pyrefly_reports_nothing(self):
        pyrefly = [d for d in self.found if d["rule"].startswith("pyrefly/")]
        self.assertEqual([], pyrefly, _show(pyrefly))

    def test_no_value_flows_as_any(self):
        leaks = [d for d in self.found if d["rule"] == "any-flow"]
        self.assertEqual([], leaks, _show(leaks))

    def test_the_gate_reports_no_error(self):
        self.assertEqual([], self.of("error"), _show(self.of("error")))

    def test_only_the_re_export_layer_reads_attributes_by_computed_name(self):
        warnings = self.of("warning")
        self.assertEqual(
            {("forbidden/dynamic-attr", "pythonx/compose/_reexport.py"): KEPT_DYNAMIC_ATTRIBUTES},
            dict(collections.Counter(
                (d["rule"], Path(d["path"]).relative_to(REPO).as_posix()) for d in warnings
            )),
            _show(warnings),
        )


if __name__ == "__main__":
    unittest.main()
