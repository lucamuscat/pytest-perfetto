import threading
from contextlib import contextmanager
from typing import Callable, Dict, Generator, List, Optional, Sequence, Union

import pyinstrument

from perfsephone import BeginDurationEvent, Category, EndDurationEvent, SerializableEvent
from perfsephone.perfetto_renderer import render

Subscriber = Callable[[List[SerializableEvent]], None]


class Profiler:
    def __init__(self) -> None:
        self.thread_ids: Dict[int, int] = {}
        self.subscribers: List[Subscriber] = []

    @contextmanager
    def __call__(
        self,
        root_frame_name: str,
        is_async: bool = False,
        args: Optional[Dict[str, Union[str, Sequence[str]]]] = None,
    ) -> Generator[List[SerializableEvent], None, None]:
        if args is None:
            args = {}

        thread_ident = threading.get_ident()

        thread_id = self.thread_ids.get(thread_ident)

        if thread_id is None:
            self.thread_ids[thread_ident] = len(self.thread_ids) + 1
            thread_id = self.thread_ids[thread_ident]

        result: List[SerializableEvent] = []
        start_event = BeginDurationEvent(
            name=root_frame_name, cat=Category("test"), args=args, tid=thread_id
        )

        result.append(start_event)
        profiler_async_mode = "enabled" if is_async else "disabled"
        with pyinstrument.Profiler(async_mode=profiler_async_mode) as profile:
            yield result
        end_event = EndDurationEvent(tid=thread_id)
        start_rendering_event = BeginDurationEvent(
            name="[pytest-perfetto] Dumping frames", cat=Category("pytest"), tid=thread_id
        )
        if profile.last_session is not None:
            result += render(profile.last_session, start_time=start_event.ts, tid=thread_id)
        end_rendering_event = EndDurationEvent(tid=thread_id)
        result += [end_event, start_rendering_event, end_rendering_event]
        self.notify(result)

    def subscribe(self, subscriber: Subscriber) -> None:
        self.subscribers.append(subscriber)

    def notify(self, result: List[SerializableEvent]) -> None:
        for subscriber in self.subscribers:
            subscriber(result)
