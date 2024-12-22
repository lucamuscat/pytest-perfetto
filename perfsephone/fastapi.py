import functools
from typing import Any, Callable

import perfsephone
import perfsephone.profiler

try:
    from fastapi.routing import APIRouter

    def __profiler_wrapper(
        profiler: perfsephone.profiler.Profiler, endpoint: Callable[..., Any]
    ) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with profiler(root_frame_name=endpoint.__name__):
                result = endpoint(*args, **kwargs)
            return result

        return wrapper

    def install_fastapi_hook(profiler: perfsephone.profiler.Profiler) -> None:
        def __add_route_wrapper(
            router: APIRouter,
            path: str,
            endpoint: Callable[..., Any],
            **kwargs: Any,
        ) -> None:
            # APIRoute is deriving the response model using `get_typed_return_annotation`. The
            # `__profiler_wrapper` must produce the same method signature as the endpoint itself.
            profiler_wrapper = functools.update_wrapper(
                __profiler_wrapper(profiler, endpoint), endpoint
            )
            APIRouter.__original_add_api_route__(router, path, profiler_wrapper, **kwargs)  # type: ignore

        APIRouter.__original_add_api_route__ = APIRouter.add_api_route  # type: ignore
        APIRouter.add_api_route = __add_route_wrapper  # type: ignore

except ImportError:

    def install_fastapi_hook(profiler: perfsephone.profiler.Profiler) -> None: ...
