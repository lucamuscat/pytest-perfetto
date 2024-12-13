"""
The pytest-perfetto plugin aims to help developers profile their tests by ultimately producing a
'perfetto' trace file, which may be natively visualized using most Chromium-based browsers.
"""

import functools
import inspect
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

import pyinstrument
import pytest
from _pytest.config import Notset
from xdist.workermanage import WorkerController

from pytest_perfetto import (
    BeginDurationEvent,
    Category,
    EndDurationEvent,
    InstantEvent,
    SerializableEvent,
    Timestamp,
)
from pytest_perfetto.perfetto_renderer import render

PERFETTO_ARG_NAME: Final[str] = "perfetto_path"
START_COLLECTION_NAME: Final[str] = "Start Collection"


class PytestPerfettoPlugin:
    def __init__(self) -> None:
        self.events: List[SerializableEvent] = []

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionstart(self) -> Generator[None, None, None]:
        # Called after the `Session` object has been created and before performing collection and
        # entering the run test loop.
        self.events.append(
            BeginDurationEvent(
                name="pytest session",
                cat=Category("pytest"),
            )
        )
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> Generator[None, None, None]:
        # Called after whole test run finished, right before returning the exit status to the system
        # https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_sessionfinish
        self.events.append(EndDurationEvent())
        perfetto_path: Union[Path, Notset] = session.config.getoption("perfetto_path")
        if isinstance(perfetto_path, Path):
            with perfetto_path.open("w") as file:
                result = [asdict(event) for event in self.events]
                for event in result:
                    # Python's time.time() produces timestamps using a seconds as its granularity,
                    # whilst perfetto uses a miceosecond granularity.
                    event["ts"] /= 1e-6

                json.dump(result, file)
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_collection(self) -> Generator[None, None, None]:
        self.events.append(
            BeginDurationEvent(
                name=START_COLLECTION_NAME,
                cat=Category("pytest"),
            )
        )
        yield

    def pytest_itemcollected(self, item: pytest.Item) -> None:
        self.events.append(InstantEvent(name=f"[Item Collected] {item.nodeid}"))

    @pytest.hookimpl(hookwrapper=True)
    def pytest_collection_finish(self) -> Generator[None, None, None]:
        self.events.append(EndDurationEvent())
        yield

    # ===== Test running (runtest) hooks =====
    # https://docs.pytest.org/en/7.1.x/reference/reference.html#test-running-runtest-hooks
    @staticmethod
    def create_args_from_location(
        location: Tuple[str, Optional[int], str],
    ) -> Dict[str, Union[str, Sequence[str]]]:
        (file_name, line_number, test_name) = location

        args: Dict[str, Union[str, Sequence[str]]] = {
            "file_name": file_name,
            "test_name": test_name,
        }

        if line_number is not None:
            args["line_number"] = str(line_number)

        return args

    def pytest_runtest_logstart(
        self, nodeid: str, location: Tuple[str, Optional[int], str]
    ) -> None:
        self.events.append(
            BeginDurationEvent(
                name=nodeid,
                args=PytestPerfettoPlugin.create_args_from_location(location),
                cat=Category("test"),
            )
        )

    def pytest_runtest_logfinish(self) -> None:
        self.events.append(EndDurationEvent())

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when is None or report.when == "call":
            return

        self.events.append(
            BeginDurationEvent(name=report.when, cat=Category("test"), ts=Timestamp(report.start))
        )
        self.events.append(EndDurationEvent(ts=Timestamp(report.stop)))

    @pytest.hookimpl(hookwrapper=True)
    def pytest_pyfunc_call(self, pyfuncitem: pytest.Function) -> Generator[None, None, None]:
        start_event = BeginDurationEvent(name="call", cat=Category("test"))
        self.events.append(start_event)
        is_async = inspect.iscoroutinefunction(pyfuncitem.function)
        profiler_async_mode = "enabled" if is_async else "disabled"
        with pyinstrument.Profiler(async_mode=profiler_async_mode) as profile:
            yield
        if profile.last_session is not None:
            self.events += render(profile.last_session, start_time=start_event.ts)
        self.events.append(EndDurationEvent())

    # ===== Reporting hooks =====
    @pytest.hookimpl(hookwrapper=True)
    def pytest_fixture_setup(
        self, fixturedef: pytest.FixtureDef[Any]
    ) -> Generator[None, None, None]:
        args = {
            "argnames": fixturedef.argnames,
            "baseid": fixturedef.baseid,
            # `fixturedef.params` are not guaranteed to serializable via json.dump(s), as a param
            # can be a sequence of objects of any type.
            "params": list(map(str, fixturedef.params)) if fixturedef.params else "",
            "scope": fixturedef.scope,
        }
        self.events.append(
            BeginDurationEvent(name=fixturedef.argname, cat=Category("test"), args=args)
        )
        yield
        self.events.append(EndDurationEvent())
        pass


# TODO: Ensure that plugin is not registered if the xdist plugin is not registered.

COLLECT_START_TIMESTAMP_KEY: pytest.StashKey[Dict[str, float]] = pytest.StashKey()
WORKER_PID_ID: pytest.StashKey[Dict[str, int]] = pytest.StashKey()
# EVENTS: pytest.StashKey[List[SerializableEvent]] = pytest.StashKey()


class XDistExperimentPlugin:
    """pytest-xdist hooks are defined
    [here](https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/newhooks.py)"""

    def __init__(self, config: pytest.Config) -> None:
        self.workers: List[WorkerController] = []
        self.config = config
        self.serializable_events: List[SerializableEvent] = []

    def process_from_remote_wrapper(self, f: Callable[..., None], node: WorkerController) -> Any:
        """pytest-xdist does not track how long the collection phase takes. Although pytest-xdist
        offers a hook that's triggered when collection is finished
        (`pytest_xdist_node_collection_finished`), it does not provide a hook for tracking when the
        collection starts.

        Internally, pytest-xdist's 'controller' worker (i.e., the worker that coordinates the test
        runner processes) receives messages from said test runner processes through an execnet
        gateway/channel, these messages are centrally processed in a method called
        `process_from_remote`.

        By intercepting calls to this internal method, which is what we are doing with this
        wrapper, we can approximate when a node has started collection.
        """

        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            message_name: str = args[0][0]
            if message_name == "collectionstart":
                stash = node.config.stash
                stash[COLLECT_START_TIMESTAMP_KEY] = {
                    str(node.gateway.id): time.time(),
                    **stash.get(COLLECT_START_TIMESTAMP_KEY, {}),
                }
            return f(*args, **kwargs)

        return wrapper

    def pytest_xdist_setupnodes(self, config: pytest.Config) -> None:
        config.stash[WORKER_PID_ID] = {}

    def pytest_configure_node(self, node: WorkerController) -> None:
        print("pytest_configure_node", node)
        node.process_from_remote = self.process_from_remote_wrapper(node.process_from_remote, node)
        self.workers.append(node)
        self.config.stash[WORKER_PID_ID] = {
            # Have the pid numbers start from one.
            node.gateway.id: len(self.config.stash[WORKER_PID_ID]) + 1
        }

    def pytest_xdist_node_collection_finished(self, node: WorkerController) -> None:
        collection_finished_timestmap: Timestamp = Timestamp(time.time())
        worker_id: str = node.gateway.id

        start_collection_timestamp: Optional[float] = self.config.stash[
            COLLECT_START_TIMESTAMP_KEY
        ].get(worker_id)

        if start_collection_timestamp is None:
            raise ValueError(
                f"The timestamp of when collection started for node {node.gateway.id} does not"
                " exist"
            )

        pid: Optional[int] = self.config.stash[WORKER_PID_ID].get(worker_id)

        if pid is None:
            raise ValueError(f"The pid for node '{worker_id}' was not created")

        self.serializable_events.append(
            BeginDurationEvent(
                name=START_COLLECTION_NAME,
                cat=Category("pytest"),
                ts=Timestamp(start_collection_timestamp),
                pid=pid,
            )
        )

        self.serializable_events.append(EndDurationEvent(pid=pid, ts=collection_finished_timestmap))

    def pytest_testnodeready(self, node: WorkerController) -> None: ...

    def pytest_sessionfinish(self) -> None:
        print(self.config.stash.get(cast(pytest.StashKey[object], COLLECT_START_TIMESTAMP_KEY), {}))


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
    config.pluginmanager.register(PytestPerfettoPlugin())
    config.pluginmanager.register(XDistExperimentPlugin(config=config))
