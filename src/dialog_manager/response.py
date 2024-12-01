from typing import Any
from .request import DialogRequest
from .status import DialogStatus

class DialogResponse:
    def __init__(self, req: DialogRequest):
        # If user doesn't provide any dialog status himself, we assume IDLE as its default value
        self._response_storage: dict[str, Any] = \
            {'dialog_status': DialogStatus.IDLE, 'persistence': [], 'user_data': {}}

        # Transfer persistence from request in case it's present
        for key in req.persistence:
            self._response_storage['user_data'][key] = req.user_data[key]

        self._response_storage['persistence'] = req.persistence.copy()

        self._full_response = {
            'version': req.version,
            'session': req.session,
            'response': {
                'text': '',
                'end_session': False
            },
            'session_state': None  # Substitute with _response_user_data directly before returning final response
        }

    @staticmethod
    def from_request(req: DialogRequest):
        return DialogResponse(req)

    def send_user_data(self, entries: dict, persistent: bool=False) -> None:
        # There's practically no need for entries type checking, as everything's going to be JSON-serialized later
        if persistent:
            self._response_storage['persistence'].extend(list(entries.keys()))

        self._response_storage['user_data'].update(entries)

    def drop_persistent_user_data(self, *args) -> None:
        # Used in cases where data is stored over the course of a few subsequent callbacks, and is removed afterward
        for arg in args:
            if arg not in self._response_storage['persistence']:
                raise KeyError('Key not found in persistent storage. Cannot be dropped.')

            self._response_storage['persistence'].remove(arg)
            del self._response_storage['user_data'][arg]

    def send_status(self, value: DialogStatus) -> None:
        # Strict instance checking to prevent unexpected exceptions later (i.e. KeyError on the following request)
        if not isinstance(value, DialogStatus):
            raise TypeError(f'{value} is not a valid DialogStatus entry.')

        self._response_storage['dialog_status'] = value

    def send_message(self, text: str) -> None:
        # Explicit type casting is required in order to execute len() and concatenation below
        if not isinstance(text, str):
            text = str(text)

        if len(text) == 0:  # Empty strings seem undesirable in terms of user experience
            raise ValueError('Cannot send empty string.')

        # If there are multiple strings to send, we simply stack them together with '\n'
        if len(self._full_response['response']['text']) == 0:
            self._full_response['response']['text'] = text
        else:
            self._full_response['response']['text'] += '\n' + text

    @property
    def json(self) -> dict:
        # Copying is necessary to prevent original data from unsafe modification
        response = self._full_response.copy()
        response['session_state'] = self._response_storage.copy()

        return response
