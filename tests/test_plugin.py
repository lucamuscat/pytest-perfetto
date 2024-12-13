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


def test_given_non_serializable_params__when_dump_trace__then_file_is_written(
    pytester: pytest.Pytester, temp_perfetto_file_path: Path
) -> None:
    pytester.makepyfile("""
        import pytest
        from uuid import uuid4

        class NotJsonSerializable:
            def __init__(self) -> None:
                self.hello = "world"

        @pytest.fixture(params=[NotJsonSerializable(), uuid4()])
        def some_fixture(request) -> None:
            ...

        @pytest.mark.parametrize("some_fixture", [uuid4()], indirect=True)
        def test_hello(some_fixture) -> None:
            ...
    """)
    result = pytester.runpytest_subprocess(f"--perfetto={temp_perfetto_file_path}")
    result.assert_outcomes(passed=1)
    assert temp_perfetto_file_path.exists()
