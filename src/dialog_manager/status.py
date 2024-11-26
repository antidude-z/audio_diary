from enum import Enum

class DialogStatus(str, Enum):
    IDLE = 0
    NEW_NOTE = 1
    INPUT_TITLE = 2
    INPUT_NOTE = 3
    DELETE_NOTE = 4
    INPUT_DEL_NOTE = 5
    INPUT_DEL_NOTE_BY_DATE = 6
    FIND_NOTE = 7
    INPUT_FIND_NOTE_BY_DATE = 8
    LIST_ALL_NOTES = 9
    SELECT_FORM = 10

INTENT_STATUS_MAP = {
    'new_note': DialogStatus.NEW_NOTE,
    'del_note': DialogStatus.DELETE_NOTE,
    'find_note': DialogStatus.FIND_NOTE,
    'list_all_notes': DialogStatus.LIST_ALL_NOTES
}
