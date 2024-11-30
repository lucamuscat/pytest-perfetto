from pathlib import Path
from typing import Dict, List, Optional

import pluggy
import pytest
from pyinstrument.frame import Frame
from pyinstrument.renderers.speedscope import (
    SpeedscopeEventType,
    SpeedscopeFrame,
    SpeedscopeRenderer,
)
from pyinstrument.session import Session

from pytest_perfetto import (
    BeginDurationEvent,
    Category,
    EndDurationEvent,
    SerializableEvent,
    Timestamp,
)

BLACKLISTED_PYTEST_LOCATIONS: List[str] = [
    str(Path(pytest.__file__).parent),
    str(Path(pluggy.__file__).parent),
]


def is_pytest_related_frame(frame: Frame) -> bool:
    for blacklisted_location in BLACKLISTED_PYTEST_LOCATIONS:
        if frame.file_path and blacklisted_location in frame.file_path:
            return True
    return False


class RootFrameCannotBeHoistedException(Exception):
    """The root frame cannot be hoisted"""


def hoist(frame: Frame) -> None:
    """Removes the frame `frame`, placing the removed frame's children in its place."""
    if frame.parent is None:
        raise RootFrameCannotBeHoistedException()
    frame.parent.add_children(frame.children, after=frame)
    frame.remove_from_parent()  # type: ignore


def render(session: Session, start_time: float) -> List[SerializableEvent]:
    renderer = SpeedscopeRenderer()
    root_frame = session.root_frame()
    if root_frame is None:
        return []

    events = renderer.render_frame(root_frame)

    perfetto_events: List[SerializableEvent] = []
    inverted_speedscope_index: Dict[int, SpeedscopeFrame] = {
        v: k for (k, v) in renderer._frame_to_index.items()
    }

    for speedscope_event in events:
        speedscope_frame: Optional[SpeedscopeFrame] = inverted_speedscope_index.get(
            speedscope_event.frame
        )
        file: Optional[str] = speedscope_frame.file if speedscope_frame else None
        line: Optional[int] = speedscope_frame.line if speedscope_frame else None
        name: Optional[str] = speedscope_frame.name if speedscope_frame else None
        timestamp: Timestamp = Timestamp(speedscope_event.at + start_time)
        if speedscope_event.type == SpeedscopeEventType.OPEN:
            perfetto_events.append(
                BeginDurationEvent(
                    name=inverted_speedscope_index[speedscope_event.frame].name or "nothing",
                    cat=Category("runtime"),
                    ts=timestamp,
                    args={"file": file, "line": line, "name": name},
                )
            )
        elif speedscope_event.type == SpeedscopeEventType.CLOSE:
            perfetto_events.append(EndDurationEvent(ts=timestamp))

    return perfetto_events
