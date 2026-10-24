"""`DefaultCoroutineScope` and `MainCoroutineScope` in `pythonx.compose.runtime` (issue #94, SPEC S5.7).

INTENT section 5.10: `DefaultCoroutineScope()` is `CoroutineScope(Dispatchers.Default)` and
`MainCoroutineScope()` is `CoroutineScope(Dispatchers.Main)`, built on `pythonx.concurrent`.
`UI.ipynb` cell 5 imports both from `pythonx.compose.runtime`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
CONCURRENT_REPO = REPO.parents[2] / "pythonx-concurrent"
if not CONCURRENT_REPO.is_dir():
    CONCURRENT_REPO = REPO.parent / "pythonx-concurrent"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _ensure_concurrent_on_path() -> bool:
    if importlib.util.find_spec("pythonx.concurrent") is not None:
        return True
    if CONCURRENT_REPO.is_dir():
        import pythonx

        concurrent_pkg = CONCURRENT_REPO / "pythonx"
        if str(concurrent_pkg) not in pythonx.__path__:
            pythonx.__path__.append(str(concurrent_pkg))
        if str(CONCURRENT_REPO) not in sys.path:
            sys.path.insert(0, str(CONCURRENT_REPO))
        return importlib.util.find_spec("pythonx.concurrent") is not None
    return False


class CoroutineScopesSurface(unittest.TestCase):
    """Both factories are exported from `pythonx.compose.runtime` and fail clearly if `pythonx-concurrent` is absent."""

    def test_both_names_are_importable_from_runtime_and_listed_in_dir(self) -> None:
        import pythonx.compose.runtime as runtime
        from pythonx.compose.runtime import DefaultCoroutineScope, MainCoroutineScope

        self.assertTrue(callable(DefaultCoroutineScope))
        self.assertTrue(callable(MainCoroutineScope))
        self.assertIn("DefaultCoroutineScope", dir(runtime))
        self.assertIn("MainCoroutineScope", dir(runtime))

    def test_missing_pythonx_concurrent_raises_runtime_error_naming_it(self) -> None:
        import pythonx.compose.runtime as runtime

        with mock.patch.dict(sys.modules, {"pythonx.concurrent": None}):
            with self.assertRaises(RuntimeError) as ctx1:
                runtime.DefaultCoroutineScope()
            self.assertIn("pythonx-concurrent", str(ctx1.exception))
            with self.assertRaises(RuntimeError) as ctx2:
                runtime.MainCoroutineScope()
            self.assertIn("pythonx-concurrent", str(ctx2.exception))


class CoroutineScopesWithConcurrent(unittest.IsolatedAsyncioTestCase):
    """Against `pythonx.concurrent`, `DefaultCoroutineScope()` and `MainCoroutineScope()` return `CoroutineScope`s."""

    def setUp(self) -> None:
        if sys.version_info < (3, 15):
            self.skipTest("pythonx-concurrent requires Python 3.15 or later")
        if not _ensure_concurrent_on_path():
            self.skipTest("pythonx.concurrent is not installed or checked out beside pythonx-compose")

    async def test_default_and_main_coroutine_scopes_launch_and_cancel(self) -> None:
        import pythonx.concurrent as pc
        from pythonx.compose.runtime import DefaultCoroutineScope, MainCoroutineScope

        default_scope = DefaultCoroutineScope()
        main_scope = MainCoroutineScope()
        try:
            self.assertIsInstance(default_scope, pc.CoroutineScope)
            self.assertIsInstance(main_scope, pc.CoroutineScope)
            self.assertIs(default_scope.dispatcher, pc.Dispatchers.Default)
            self.assertIs(main_scope.dispatcher, pc.Dispatchers.Main)

            ran = threading.Event()

            async def worker(v: int) -> int:
                await asyncio.sleep(0.005)
                ran.set()
                return v + 1

            job = default_scope.launch(worker, 41)
            self.assertTrue(ran.wait(timeout=2.0))
            await default_scope.join()
            self.assertTrue(job.done())
        finally:
            default_scope.cancel()
            main_scope.cancel()


if __name__ == "__main__":
    unittest.main()
