from enum import Enum

CALLBACKS = {}

class DialogStatus(str, Enum):
    IDLE = 0
    NEW_NOTE = 1
    INPUT_NAME = 2
    INPUT_NOTE = 3
    DELETE_NOTE = 4
    INPUT_DEL_NOTE = 5
    INPUT_DEL_NOTE_BY_DATE = 6
    FIND_NOTE = 7
    INPUT_FIND_NOTE_BY_DATE = 8

INTENT_STATUS_MAP = {
    'new_note': DialogStatus.NEW_NOTE,
    'del_note': DialogStatus.DELETE_NOTE,
    'find_note': DialogStatus.FIND_NOTE
}


def status_handler(status_id: DialogStatus):
    def inner(func):
        def wrapper(req: DialogRequest, res: DialogResponse):
            func(req, res)
            return res.json

        CALLBACKS[status_id] = wrapper
        return wrapper

    return inner

class DialogRequest:
    def __init__(self, request: dict):
        self.user_id = request['session']['user']['user_id']
        self.is_new_session = request['session']['new']
        self.user_input = (request['request']['original_utterance']).lower()
        self.nlu_tokens = request['request']['nlu']['tokens']
        self.status: DialogStatus = DialogStatus.IDLE

        self._request_user_data: dict = request['state']['session']

        if 'dialog_status' in self._request_user_data:
            self.status = self._request_user_data['dialog_status']
            del self._request_user_data['dialog_status']

        intents: dict = request['request']['nlu']['intents']

        if self.status == DialogStatus.IDLE:
            for intent in INTENT_STATUS_MAP:
                if intents.get(intent) is not None:
                    self.status = INTENT_STATUS_MAP[intent]
                    break

    @property
    def user_data(self) -> dict:
        return self._request_user_data.copy()


class DialogResponse:
    def __init__(self, request: dict):
        self._response_user_data = {'dialog_status': DialogStatus.IDLE}

        self._full_response = {
            'version': request['version'],
            'session': request['session'],
            'response': {
                'text': '',
                'end_session': False
            },
            'session_state': self._response_user_data
        }

    def send_user_data(self, name, value):
        if name == 'dialog_status':
            raise ValueError('Attempt to set dialog_status outside of a corresponding function. '
                             'Use send_dialog_status() instead.')

        self._response_user_data[name] = value

    def send_status(self, value: DialogStatus) -> None:
        if type(value) != DialogStatus:
            raise TypeError(f'{value} is not a valid DialogStatus entry.')

        self._response_user_data['dialog_status'] = value

    def send_message(self, text):
        if len(self._full_response['response']['text']) == 0:
            self._full_response['response']['text'] = text
        else:
            self._full_response['response']['text'] += '\n' + text

    @property
    def json(self):
        return self._full_response.copy()
