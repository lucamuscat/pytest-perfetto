import functools
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, List

import pyinstrument
from fastapi.routing import APIRouter


@dataclass(frozen=True)
class FastAPIProfiler:
    profiler: pyinstrument.Profiler
    thread_id: int
    start_time: float


PROFILERS: List[FastAPIProfiler] = []


def __profiler_wrapper(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time: float = time.time()
        with pyinstrument.Profiler() as profiler:
            result = endpoint(*args, **kwargs)
        PROFILERS.append(
            FastAPIProfiler(
                profiler=profiler, thread_id=threading.get_ident(), start_time=start_time
            )
        )
        return result

    return wrapper


def __add_route_wrapper(
    router: APIRouter, path: str, endpoint: Callable[..., Any], **kwargs: Any
) -> None:
    # APIRoute is deriving the response model using `get_typed_return_annotation`. The
    # `__profiler_wrapper` must produce the same method signature as the endpoint itself.
    profiler_wrapper = functools.update_wrapper(__profiler_wrapper(endpoint), endpoint)
    APIRouter.__original_add_api_route__(router, path, profiler_wrapper, **kwargs)  # type: ignore


APIRouter.__original_add_api_route__ = APIRouter.add_api_route
APIRouter.add_api_route = __add_route_wrapper
