"""
The pytest-perfetto plugin aims to help developers profile their tests by ultimately producing a
'perfetto' trace file, which may be natively visualized using most Chromium-based browsers.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Final, Generator, List, Literal, NewType, Optional, Tuple, Union

import pytest
from _pytest.config import Notset

Category = NewType("Category", str)
Timestamp = NewType("Timestamp", float)
PERFETTO_ARG_NAME: Final[str] = "perfetto_path"


class TraceEvent:
    """
    The Trace Event Format is the trace data representation that is processed by the Trace
    Viewer. [This document is the canonical reference on the 'Trace Event Format'](https://docs.google.com/document/d/1CvAClvFfyA5R-PhYUmn5OOQtYMH4h6I0nSsKchNAySU/preview?tab=t.0)
    """

    ...


class Phase(str, Enum):
    """
    The phase describes the event's type. The phase is a single character which changes depending on
    the type of event. This class encapsulates all the valid phase types.

    The following is a description of some of the valid event types:

    * Duration Events:
        Duration events provide a way of marking a duration of work on a given thread. Duration
        events are marked by the 'B' & 'E' phase types. The 'B' event must come before the 'E'
        event. 'B' & 'E' events may be nested, allowing the capturing of function calling behaviour
        on a thread. The timestamps for duration events must be in an increasing order for a given
        thread. Timestamps in different threads do not have to be in increasing order.
    * Instant Events:
        Instant events, or points in time, that correspond to an event that happens but has no
        associated duration.
    """

    B = "B"
    """Marks the beginning of a duration event."""
    E = "E"
    """Marks the end of a duration event."""
    i = "i"
    """Marks an instant event."""


@dataclass(frozen=True)
class DurationEvent: ...


@dataclass(frozen=True)
class BeginDurationEvent(DurationEvent):
    name: str
    cat: Category
    ts: Timestamp = field(default_factory=lambda: Timestamp(time.time()))
    pid: int = 1
    tid: int = 1
    args: Dict[str, Any] = field(default_factory=dict)
    ph: Literal[Phase.B] = Phase.B


@dataclass(frozen=True)
class EndDurationEvent(DurationEvent):
    pid: int = 1
    tid: int = 1
    ts: Timestamp = field(default_factory=lambda: Timestamp(time.time()))
    ph: Literal[Phase.E] = Phase.E


class InstantScope(str, Enum):
    """Specifies the scope of the instant event. The scope of the event designates how tall to draw
    the instant even in Trace Viewer."""

    g = "g"
    """Global scoped instant event. A globally scoped event will draw a line from the top to the
    bottom of the timeline."""
    p = "p"
    """Process scoped instant event. A process scoped instant event will draw through all threads of
    a given process."""
    t = "t"
    """Thread scoped instant event. A thread scoped instant event will draw the height of a single
    thread."""


@dataclass(frozen=True)
class InstantEvent(TraceEvent):
    name: str
    pid: int = 1
    tid: int = 1
    ts: Timestamp = field(default_factory=lambda: Timestamp(time.time()))
    ph: Literal[Phase.i] = Phase.i
    s: InstantScope = InstantScope.t


events: List[Union[DurationEvent, InstantEvent]] = []


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionstart() -> Generator[None, None, None]:
    # Called after the `Session` object has been created and before performing collection and
    # entering the run test loop.
    events.append(
        BeginDurationEvent(
            name="pytest session",
            cat=Category("pytest"),
        )
    )
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_sessionfinish(session: pytest.Session) -> Generator[None, None, None]:
    # Called after whole test run finished, right before returning the exit status to the system
    # https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_sessionfinish
    events.append(EndDurationEvent())
    perfetto_path: Union[Path, Notset] = session.config.getoption("perfetto_path")
    if isinstance(perfetto_path, Path):
        with perfetto_path.open("w") as file:
            json.dump([asdict(event) for event in events], file)
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_collection() -> Generator[None, None, None]:
    events.append(
        BeginDurationEvent(
            name="Start Collection",
            cat=Category("pytest"),
        )
    )
    yield


def pytest_itemcollected(item: pytest.Item) -> None:
    events.append(InstantEvent(name=f"[Item Collected] {item.nodeid}"))


@pytest.hookimpl(hookwrapper=True)
def pytest_collection_finish() -> Generator[None, None, None]:
    events.append(EndDurationEvent())
    yield


# ===== Test running (runtest) hooks =====
# https://docs.pytest.org/en/7.1.x/reference/reference.html#test-running-runtest-hooks


def create_args_from_location(location: Tuple[str, Optional[int], str]) -> Dict[str, str]:
    (file_name, line_number, test_name) = location

    args = {"file_name": file_name, "test_name": test_name}

    if line_number is not None:
        args["line_number"] = str(line_number)

    return args


def pytest_runtest_logstart(nodeid: str, location: Tuple[str, Optional[int], str]) -> None:
    events.append(
        BeginDurationEvent(
            name=nodeid,
            args=create_args_from_location(location),
            cat=Category("test"),
        )
    )


def pytest_runtest_logfinish() -> None:
    events.append(EndDurationEvent())


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when is None:
        return

    events.append(
        BeginDurationEvent(name=report.when, cat=Category("test"), ts=Timestamp(report.start))
    )
    events.append(EndDurationEvent(ts=Timestamp(report.stop)))


# ===== Reporting hooks =====


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef: pytest.FixtureDef[Any]) -> Generator[None, None, None]:
    args = {
        "argnames": fixturedef.argnames,
        "baseid": fixturedef.baseid,
        "ids": fixturedef.ids,
        "params": fixturedef.params,
        "scope": fixturedef.scope,
    }
    events.append(BeginDurationEvent(name=fixturedef.argname, cat=Category("test"), args=args))
    yield
    events.append(EndDurationEvent())
    pass


# ===== Initialization hooks =====
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--perfetto",
        dest=PERFETTO_ARG_NAME,
        metavar=PERFETTO_ARG_NAME,
        action="store",
        type=Path,
        help="The file path for the trace file generated by the `pytest-perfetto` plugin.",
    )


def pytest_configure(config: pytest.Config) -> None:
    option: Union[Path, Notset] = config.getoption(PERFETTO_ARG_NAME)
    if isinstance(option, Path) and option.is_dir():
        raise ValueError("The provided path must not be a directory")
