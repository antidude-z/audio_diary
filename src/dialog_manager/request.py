"""A module implementing DialogRequest class."""

from typing import Any, Union, Dict, List

from .status import DialogStatus, INTENT_STATUS_MAP


class DialogRequest:
    """A class that offers useful shortcuts for requests following Alice request protocol."""

    def __init__(self, aio_request: dict):
        self.version: str = aio_request['version']

        # Every session-related attribute is defined here
        self.session: Dict = aio_request['session']
        self.user_id: str = self.session['user']['user_id']
        self.is_new_session: bool = self.session['new']

        # Every request-related attribute is defined here
        self.request: Dict = aio_request['request']
        self.user_input: str = self.request['original_utterance']  # Unmodified input received 'as is'

        # For short input parsing purposes, has some useful text transformations compared to self.user_input
        self.command: str = self.request['command'].lower()

        # Basically self.command, but split into words
        self.nlu_tokens: List[str] = list(map(lambda x: x.lower(), self.request['nlu']['tokens']))

        self.intents: Dict[str, Any] = self.request['nlu']['intents']  # Used for advanced user speech recognition

        self._request_storage: Dict[str, Any] = aio_request['state']['session']

        # In case of new session, when session storage is initially empty, we begin with IDLE by default
        self.status: DialogStatus = DialogStatus.IDLE

        self.persistence: List[str] = []

        # If it's not a new session, we get current dialog status and persistence data directly from the storage
        if not self.is_new_session:
            self.status = self._request_storage['dialog_status']
            self.persistence = self._request_storage['persistence']

        self.exit_current_status: bool = False

        # 'exit' is a special intent which interrupts any dialog process and sets the status back to IDLE
        if 'exit' in self.intents and self.status != DialogStatus.IDLE:
            self.status = DialogStatus.IDLE
            self.exit_current_status = True

        # IDLE means we are waiting for a command-type intent to fire,
        # and if so, we replace this status with an intent-related one
        # In other case, it's either new session or the user has submitted an unrecognizable input
        if self.status == DialogStatus.IDLE and not self.exit_current_status:
            for intent in self.intents:
                if intent in INTENT_STATUS_MAP:
                    self.status = INTENT_STATUS_MAP[intent]
                    break

    @property
    def user_data(self) -> Dict[str, Any] | None:
        # Making a copy to keep original user data immutable
        if 'user_data' in self._request_storage:
            return self._request_storage['user_data'].copy()
