from __future__ import annotations

import asyncio
import inspect

import pytest


try:  # pragma: no cover - optional dependency check
    import pytest_asyncio  # noqa: F401
except ImportError:  # pragma: no cover - fallback runner for async tests

    @pytest.hookimpl(tryfirst=True)
    def pytest_pyfunc_call(pyfuncitem):
        if inspect.iscoroutinefunction(pyfuncitem.obj):
            signature = inspect.signature(pyfuncitem.obj)
            kwargs = {
                name: pyfuncitem.funcargs[name]
                for name in signature.parameters
                if name in pyfuncitem.funcargs
            }
            asyncio.run(pyfuncitem.obj(**kwargs))
            return True
        return None
