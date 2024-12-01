from pathlib import Path

import pytest


def test_given_perfetto_arg_trace_files_are_written(
    pytester: pytest.Pytester, temp_perfetto_file_path: Path
) -> None:
    pytester.makepyfile("""
        def test_hello(): ...
    """)
    result = pytester.runpytest_subprocess(f"--perfetto={temp_perfetto_file_path}")
    result.assert_outcomes(passed=1)
    assert temp_perfetto_file_path.exists()
