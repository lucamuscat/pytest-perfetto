from pathlib import Path
from uuid import uuid4

import pytest


def test_given_perfetto_arg_trace_files_are_written(
    pytester: pytest.Pytester, tmp_path: Path
) -> None:
    perfetto_arg_value: Path = tmp_path / f"{uuid4().hex}.json"
    pytester.makepyfile("""
        def test_hello(): ...
    """)
    result = pytester.runpytest_subprocess(f"--perfetto={perfetto_arg_value}")
    result.assert_outcomes(passed=1)
    assert perfetto_arg_value.exists()
