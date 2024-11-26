from typing import Any
from .status import DialogStatus

class DialogResponse:
    def __init__(self, request: dict):
        # If user doesn't provide any dialog status himself, we assume IDLE as its default value
        self._response_user_data: dict[str, Any] = {'dialog_status': DialogStatus.IDLE}

        self._full_response = {
            'version': request['version'],
            'session': request['session'],
            'response': {
                'text': '',
                'end_session': False
            },
            'session_state': None  # Substitute with _response_user_data directly before returning final response
        }

    #TODO: add dict support
    def send_user_data(self, name: str, value: Any) -> None:
        # There's practically no need for type checking here, as everything's going to be JSON-serialized later
        if name == 'dialog_status':
            raise ValueError('Attempt to set dialog_status outside of a corresponding function. '
                             'Use send_status() instead.')

        self._response_user_data[name] = value

    def send_status(self, value: DialogStatus) -> None:
        # Strict instance checking to prevent unexpected exceptions later (i.e. KeyError on the following request)
        if not isinstance(value, DialogStatus):
            raise TypeError(f'{value} is not a valid DialogStatus entry.')

        self._response_user_data['dialog_status'] = value

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
        response['session_state'] = self._response_user_data.copy()

        return response
