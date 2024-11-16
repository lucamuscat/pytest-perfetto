"""
The pytest-perfetto plugin aims to help developers profile their tests by ultimately producing a
'perfetto' trace file, which may be natively visualized using most Chromium-based browsers.
"""

import json
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Generator, List, Literal, NewType, Optional

import pytest

Category = NewType("Category", str)
Timestamp = NewType("Timestamp", float)


class TraceEvent:
    """
    The Trace Event Format is the trace data representation that is processed byt he Trace
    Viewer. [This document is the canonical reference on the 'Trace Event Format'](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview?tab=t.0)
    """

    ...


class Phase(str, Enum):
    """
    The phase described the event type. This is a single character which changes depending on the
    type of event being output. This class will encapsulate all the valid phase types

    The following is a description of some of the valid event types:

    * Duration Events:
        Duration events provide a way to mark a duration of work on a given thread. Duration events
        are marked by the 'B' & 'E' phase types. The 'B' event must come before the 'E' event. 'B' &
        'E' events may be nested, allowing the capturing of function calling behaviour on a thread.
        The timestamps for duration events must be in an increasing order for a given thread.
        Timestamps in different threads do not have to be in increasing order.
    """

    B = "B"
    """Marks the beginning of a duration event."""
    E = "E"
    """Marks the end of a duration event"""


@dataclass(frozen=True)
class DurationEvent: ...


@dataclass(frozen=True)
class BeginDurationEvent(DurationEvent):
    name: str
    cat: Category
    ts: Timestamp
    pid: int
    tid: int
    args: Dict[str, Any]
    ph: Literal[Phase.B] = Phase.B


@dataclass(frozen=True)
class EndDurationEvent(DurationEvent):
    pid: int
    tid: int
    ts: Timestamp
    ph: Literal[Phase.E] = Phase.E


events: List[DurationEvent] = []


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionstart() -> Generator[None, None, None]:
    # Called after the `Session` object has been created and before performing collection and
    # entering the run test loop.
    events.append(
        BeginDurationEvent(
            name="Session Start",
            cat=Category("pytest"),
            ts=Timestamp(time.monotonic()),
            pid=1,
            tid=1,
            args={},
        )
    )
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish() -> Generator[None, None, None]:
    # Called after whole test run finished, right before returning the exit status to the system
    events.append(
        EndDurationEvent(
            pid=1,
            tid=1,
            ts=Timestamp(time.monotonic()),
        )
    )
    print(json.dumps([asdict(event) for event in events]))
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call() -> Generator[None, None, None]:
    print("Hello world")
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_collection() -> Generator[Optional[object], None, None]:
    # start = time()

    result = yield None
    # print(f"Time taken collecting tests: {time() - start}")
    return result


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(
    fixturedef: pytest.FixtureDef[Any],
) -> Generator[Optional[object], None, None]:
    # start = time()
    result = yield None
    # print(f"Fixture {fixturedef.argname} took {time() - start}s setting up")
    return result
