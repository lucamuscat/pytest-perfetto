"""
The pytest-perfetto plugin aims to help developers profile their tests by ultimately producing a
'perfetto' trace file, which may be natively visualized using most Chromium-based browsers.
"""

from time import time
from typing import Any, Generator, Optional

import pytest


class TraceEvent:
    """
    The Trace Event Format is the trace data representation that is processed byt he Trace
    Viewer. [This document is the canonical reference on the 'Trace Event Format'](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview?tab=t.0)
    """

    ...


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call() -> Generator[None, None, None]:
    print("Hello world")
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_collection() -> Generator[Optional[object], None, None]:
    start = time()

    result = yield None
    print(f"Time taken collecting tests: {time() - start}")
    return result


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(
    fixturedef: pytest.FixtureDef[Any],
) -> Generator[Optional[object], None, None]:
    start = time()
    result = yield None
    print(f"Fixture {fixturedef.argname} took {time() - start}s setting up")
    return result
