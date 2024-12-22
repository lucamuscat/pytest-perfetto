import functools
from typing import Any, Callable

from fastapi.routing import APIRouter

import perfsephone
import perfsephone.profiler

__profiler: perfsephone.profiler.Profiler = perfsephone.profiler.Profiler()


def set_profiler(profiler: perfsephone.profiler.Profiler) -> None:
    global __profiler  # noqa: PLW0603
    __profiler = profiler


def __profiler_wrapper(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # TODO: Figure out why the thread id for events in other threads is not being populated. If
        # this does not work out, ditch the whole profiler thing and pass around pyinstrument
        # sessions.
        with __profiler(root_frame_name=endpoint.__name__):
            result = endpoint(*args, **kwargs)
        return result

    return wrapper


def __add_route_wrapper(
    router: APIRouter, path: str, endpoint: Callable[..., Any], **kwargs: Any
) -> None:
    # APIRoute is deriving the response model using `get_typed_return_annotation`. The
    # `__profiler_wrapper` must produce the same method signature as the endpoint itself.
    profiler_wrapper = functools.update_wrapper(__profiler_wrapper(endpoint), endpoint)
    APIRouter.__original_add_api_route__(router, path, profiler_wrapper, **kwargs)  # type: ignore


APIRouter.__original_add_api_route__ = APIRouter.add_api_route  # type: ignore
APIRouter.add_api_route = __add_route_wrapper  # type: ignore
