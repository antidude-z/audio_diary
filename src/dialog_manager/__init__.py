from typing import Callable, Awaitable
from .status import DialogStatus
from .request import DialogRequest
from .response import DialogResponse

StatusHandler = Callable[[DialogRequest, DialogResponse], Awaitable[dict]]  # Custom type for annotations

CALLBACKS: dict[DialogStatus, StatusHandler] = {}

# The aim here is to 'register' given function as a callback for a certain dialog status
# as well as make it provide flask-friendly json output automatically
def status_handler(status_id: DialogStatus) -> Callable:
    def inner(func: StatusHandler) -> StatusHandler:
        async def wrapper(req: DialogRequest, res: DialogResponse) -> dict:
            await func(req, res)  # Decorated functions must take Request and Response as their arguments
            return res.json

        CALLBACKS[status_id] = wrapper
        return wrapper

    return inner

def get_callback(status_id: DialogStatus) -> StatusHandler:
    return CALLBACKS[status_id]
