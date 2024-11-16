from enum import Enum

response_functions = {}

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

INTENTS = {'new_note': DialogStatus.NEW_NOTE, 'del_note': DialogStatus.DELETE_NOTE, 'find_note': DialogStatus.FIND_NOTE}


def status(status_id: DialogStatus):
    def inner(func):
        def wrapper(session_storage: SessionStorage):
            func(session_storage)
            return session_storage.response
        response_functions[status_id] = wrapper
        return wrapper
    return inner

class SessionStorage:
    def __init__(self, request: dict) -> None:
        self.is_new_session = request['session']['new']
        self.user_text = (request['request']['original_utterance']).lower()
        self.user_id = request['session']['user']['user_id']
        self.tokens = request['request']['nlu']['tokens']

        self._request_storage = request['state']['session']
        self._response_storage = {'dialog_status': DialogStatus.IDLE}

        self._full_response = {
            'version': request['version'],
            'session': request['session'],
            'response': {
                'text': '',
                'end_session': False
            },
            'session_state': self._response_storage
        }

        for key, value in self._request_storage.items():
            if key[0] == '_':
                self._response_storage[key] = value

        if 'dialog_status' in self._request_storage:  # if it's not the first time a SessionStorage was initiated
            self._dialog_status = self._request_storage['dialog_status']
            del self._request_storage['dialog_status']
        else:
            self._dialog_status = DialogStatus.IDLE

        intents: dict = request['request']['nlu']['intents']
        if self._dialog_status == DialogStatus.IDLE:
            for intent in INTENTS:
                if intents.get(intent) is not None:
                    self._dialog_status = INTENTS[intent]
                    break

    @property
    def dialog_status(self) -> DialogStatus:
        return self._dialog_status

    def respond_dialog_status(self, value: DialogStatus) -> None:
        if type(value) != DialogStatus:
            raise ValueError('Value is not a valid DialogStatus entry')

        self._response_storage['dialog_status'] = value

    def __getitem__(self, item: str):
        return self._request_storage[item]

    def respond_user_data(self, item, value):
        self._response_storage[item] = value

    def respond_text(self, text):
        self._full_response['response']['text'] = text

    @property
    def response(self):
        return self._full_response

