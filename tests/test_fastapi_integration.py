import json
from pathlib import Path

import pytest


def test_given_test_client__when_run_test__then_include_route_in_separate_thread(
    pytester: pytest.Pytester, temp_perfetto_file_path: Path
) -> None:
    pytester.makepyfile("""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from typing import Dict
    import time

    def test_hello() -> None:
        app = FastAPI()

        @app.post("/foo")
        def foo() -> Dict[str, str]:
            time.sleep(0.005)
            return {"foo": "bar"}

        client = TestClient(app)

        response = client.post("/foo")
        assert response.json() == {"foo": "bar"}
    """)

    result = pytester.runpytest_subprocess(f"--perfetto={temp_perfetto_file_path}")
    result.assert_outcomes(passed=1)

    trace_file = json.load(temp_perfetto_file_path.open("r"))
    event_foo = next(event for event in trace_file if event.get("name") == "foo")
    expected_tid = 2
    assert event_foo.get("tid") == expected_tid
