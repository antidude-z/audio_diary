"""This package provides a convenient wrapper for Alice requests/responses
by utilizing our own DialogStatus-system (BETA)."""

from typing import Awaitable, Callable, Dict

from .request import DialogRequest
from .response import DialogResponse
from .status import DialogStatus
from .nlu import *

StatusHandlerType = Callable[[DialogRequest, DialogResponse], Awaitable[Dict | None]]  # Custom type for annotations

CALLBACKS: Dict[DialogStatus, StatusHandlerType] = {}


def status_handler(status_id: DialogStatus) -> Callable:
    """Register given function as a callback for a certain dialog status,
    as well as make it provide flask-friendly json output automatically.
    Decorated functions must take Request and Response as their arguments.
    """

    def inner(func: StatusHandlerType) -> StatusHandlerType:
        async def wrapper(req: DialogRequest, res: DialogResponse) -> Dict:
            await func(req, res)
            return res.json

        CALLBACKS[status_id] = wrapper
        return wrapper

    return inner


def get_handler(status_id: DialogStatus) -> StatusHandlerType:
    """Return a handler for working with `status_id` dialog status."""

    return CALLBACKS[status_id]
