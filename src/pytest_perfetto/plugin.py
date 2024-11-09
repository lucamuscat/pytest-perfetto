from typing import Generator

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call() -> Generator[None, None, None]:
    print("Hello world")
    yield
