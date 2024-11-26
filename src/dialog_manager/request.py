from typing import Any
from .status import DialogStatus, INTENT_STATUS_MAP

class DialogRequest:
    def __init__(self, request: dict):
        self.user_id: str = request['session']['user']['user_id']
        self.is_new_session: bool = request['session']['new']
        self.user_input: str = (request['request']['original_utterance']).lower()
        self.command: str = request['request']['command'].lower()  # For date parsing purposes
        self.exit_current_status: bool = False
        self.nlu_tokens: list[str] = list(map(lambda x: x.lower(), request['request']['nlu']['tokens']))  # ~ Same as command, but split into words

        # In case of new session, when session storage is initially empty, we begin with IDLE by default
        self.status: DialogStatus = DialogStatus.IDLE

        self._request_user_data: dict[str, str] = request['state']['session']

        # If a dialog status was provided, save it in 'self.status'
        if 'dialog_status' in self._request_user_data:
            self.status = self._request_user_data['dialog_status']
            del self._request_user_data['dialog_status']

        intents: dict[str, Any] = request['request']['nlu']['intents']

        # 'exit' is a special intent which interrupts any dialog process and sets the status back to IDLE no matter what
        if 'exit' in intents and self.status != DialogStatus.IDLE:
            self.status = DialogStatus.IDLE
            self.exit_current_status = True

        # IDLE means we are waiting for an intent to fire,
        # and if so, we replace this status with an intent-related one
        # In other case, it's either new session or the user has submitted an unrecognizable input
        if self.status == DialogStatus.IDLE and not self.exit_current_status:
            for intent in intents:
                if intent in INTENT_STATUS_MAP:
                    self.status = INTENT_STATUS_MAP[intent]
                    break

    @property
    def user_data(self) -> dict:
        # Making a copy to keep original user data immutable
        return self._request_user_data.copy()
