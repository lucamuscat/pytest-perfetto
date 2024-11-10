from time import time
from typing import Any, Generator, Optional

import pytest


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


