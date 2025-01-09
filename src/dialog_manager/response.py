"""A module implementing DialogResponse class."""

from typing import Any, Dict

from .status import DialogStatus
from .request import DialogRequest


class DialogResponse:
    """A class that provides interface for making correct responses to Alice."""

    def __init__(self) -> None:
        # If user doesn't provide any dialog status himself, we assume IDLE as its default value
        self.__response_storage: Dict[str, Any] = \
            {'dialog_status': DialogStatus.IDLE, 'persistence': [], 'user_data': {}}

        self.__full_response: Dict[str, Any] = {
            'response': {
                'text': '',
                'end_session': False
            },
            'session_state': None,  # Substitute with _response_user_data directly before returning final response
            'version': '1.0'
        }

    def transfer_persistence(self, req: DialogRequest) -> None:
        """Transfer persistent variables from request in case they are present."""

        for key in req.persistence:
            self.__response_storage['user_data'][key] = req.user_data[key]

        self.__response_storage['persistence'] = req.persistence.copy()

    def send_user_data(self, entries: Dict[str, Any], persistent: bool = False) -> None:
        """Store given data inside `user_data` session storage field. The data could be accessed only in the next
        request and is lost afterward unless `persistent` is set to True."""

        # There's practically no need for entries type checking, as everything's going to be JSON-serialized later
        if persistent:
            self.__response_storage['persistence'].extend(list(entries.keys()))

        self.__response_storage['user_data'].update(entries)

    def drop_persistent_user_data(self, *args) -> None:
        """Remove unnecessary fields from `user_data`. Changes will be applied on the following request."""

        # Used in cases where data is stored over the course of a few subsequent callbacks, and is removed afterward
        for arg in args:
            if arg not in self.__response_storage['persistence']:
                raise KeyError('Key not found in persistent storage. Cannot be dropped.')

            self.__response_storage['persistence'].remove(arg)
            del self.__response_storage['user_data'][arg]

    def send_status(self, value: DialogStatus) -> None:
        """Set the dialog status for the next request."""

        # Strict instance checking to prevent unexpected exceptions later (i.e. KeyError on the following request)
        if not isinstance(value, DialogStatus):
            raise TypeError(f'{value} is not a valid DialogStatus entry.')

        self.__response_storage['dialog_status'] = value

    def send_message(self, text: str) -> None:
        """Send a simple text message to the user.
        Note that this DOESN'T support text-to-speech syntax functionality."""

        # Explicit type casting is required in order to execute len() and concatenation below
        if not isinstance(text, str):
            text = str(text)

        if len(text) == 0:  # Empty strings seem undesirable in terms of user experience
            raise ValueError('Cannot send empty string.')

        # If there are multiple strings to send, we simply stack them together with '\n'
        if len(self.__full_response['response']['text']) == 0:
            self.__full_response['response']['text'] = text
        else:
            self.__full_response['response']['text'] += '\n' + text

    @property
    def json(self) -> Dict[str, Any]:
        # Copying is necessary to prevent original data from unsafe modification
        response = self.__full_response.copy()
        response['session_state'] = self.__response_storage.copy()

        return response
