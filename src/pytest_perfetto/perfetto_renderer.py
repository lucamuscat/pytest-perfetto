from pathlib import Path
from typing import Dict, Final, List, Optional, Sequence

import _pytest
import pluggy
import pytest
from pyinstrument.frame import Frame
from pyinstrument.renderers.speedscope import (
    SpeedscopeEvent,
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
    str(Path(_pytest.__file__).parent),
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


def remove_pytest_related_frames(root_frame: Frame) -> Sequence[Frame]:
    """Removes pytest related frames. May return multiple root frames in the scenario where the
    provided root frame is a pytest related frame."""
    if root_frame.children:
        for child_frame in root_frame.children:
            remove_pytest_related_frames(child_frame)

    if is_pytest_related_frame(root_frame) and root_frame.parent is None:
        return root_frame.children

    if is_pytest_related_frame(root_frame):
        hoist(root_frame)
        return []
    return [root_frame]


def render(session: Session, start_time: float) -> List[SerializableEvent]:
    renderer = SpeedscopeRenderer()
    root_frame = session.root_frame()
    if root_frame is None:
        return []

    perfetto_events: List[SerializableEvent] = []
    new_roots: List[Frame] = list(remove_pytest_related_frames(root_frame))

    def render_root_frame(root_frame: Frame) -> List[SerializableEvent]:
        result: List[SerializableEvent] = []
        events: List[SpeedscopeEvent] = renderer.render_frame(root_frame)

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
                result.append(
                    BeginDurationEvent(
                        name=inverted_speedscope_index[speedscope_event.frame].name or "nothing",
                        cat=Category("runtime"),
                        ts=timestamp,
                        args={"file": file, "line": line, "name": name},
                    )
                )
            elif speedscope_event.type == SpeedscopeEventType.CLOSE:
                result.append(EndDurationEvent(ts=timestamp))
        return result

    for root in new_roots:
        perfetto_events += render_root_frame(root)

    return perfetto_events