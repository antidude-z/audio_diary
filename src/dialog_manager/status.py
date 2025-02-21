"""A module implementing DialogStatus enum."""

from enum import Enum
from typing import Final, Dict


class DialogStatus(str, Enum):
    """A specific dialog state which invokes its own status handlers upon reception."""

    IDLE = 0
    NEW_NOTE = 1
    NEW_NOTE_TITLE_INPUT = 2
    NEW_NOTE_TEXT_INPUT = 3
    DEL_NOTE = 4
    DEL_NOTE_TITLE_INPUT = 5
    DEL_NOTE_DATE_INPUT = 6
    FIND_NOTE = 7
    FIND_NOTE_DATE_INPUT = 8
    FIND_NOTE_FORM_INPUT = 9
    LIST_ALL_NOTES = 10
    HELP_ME = 11
    WHAT_CAN_YOU_DO = 12
    FIND_NOTE_TITLE_INPUT = 13
    LIST_NEXT = 14


# We assume that all intents are connected to separate dialog statuses in order to simplify status handler logic
INTENT_STATUS_MAP: Final[Dict[str, DialogStatus]] = {
    'new_note': DialogStatus.NEW_NOTE,
    'del_note': DialogStatus.DEL_NOTE,
    'find_note': DialogStatus.FIND_NOTE,
    'list_all_notes': DialogStatus.LIST_ALL_NOTES,
    'YANDEX.HELP': DialogStatus.HELP_ME,
    'YANDEX.WHAT_CAN_YOU_DO': DialogStatus.WHAT_CAN_YOU_DO,
    'next': DialogStatus.LIST_NEXT
}
