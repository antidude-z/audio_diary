from datetime import datetime
from typing import List, Optional

from asyncpg import Record

from dialog_manager import DialogRequest, DialogResponse, DialogStatus, Intent, status_handler, EntityString
from note_storage import NoteStorage
from util import send_date_list, parse_date


async def search_attempt_by_title(req: DialogRequest, res: DialogResponse, title: str):
    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes(title)

    if len(notes) == 1:  # If there is only one note, send it back to user
        ask_note_form(res)
    elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
        send_date_list(res, notes)
        res.send_status(DialogStatus.FIND_NOTE_DATE_INPUT)
    else:
        res.send_message('Нет записи с таким названием.')

    res.send_user_data({'title': title})


def ask_note_form(res: DialogResponse) -> None:
    res.send_message('Для удобства могу сократить заметку и пересказать самые важные моменты. '
                     'Хотите?')
    res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)


@status_handler(DialogStatus.FIND_NOTE)
async def find_note(req: DialogRequest, res: DialogResponse) -> None:
    intent: Intent = req.nlu.intents['find_note']

    title: Optional[EntityString] = intent.slots.get('title')
    date: Optional[EntityString] = intent.slots.get('date')

    if title is not None and date is not None:
        # Checking if date is correct
        date_object = parse_date(res, date.value)

        if date_object is None:
            return

        # Checking if a note with given attributes exists
        async with NoteStorage(req.user_id) as db:
            notes = await db.select_notes(title.value, date_object)

        if len(notes) != 0:  # Successfully found a note
            ask_note_form(res)
            res.send_user_data({'title': title.value, 'date': date.value})
        else:  # Search failed
            res.send_message('Не нашлось заметки с таким названием за указанный день. Попробуйте ещё раз!')
    elif title is not None:
        await search_attempt_by_title(req, res, title.value)
    else:
        res.send_message('Укажите название заметки.')
        res.send_status(DialogStatus.FIND_NOTE_TITLE_INPUT)


@status_handler(DialogStatus.FIND_NOTE_TITLE_INPUT)
async def find_note_title_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.command

    await search_attempt_by_title(req, res, title)


@status_handler(DialogStatus.FIND_NOTE_DATE_INPUT)
async def find_note_date_input(req: DialogRequest, res: DialogResponse) -> None:
    date_str: str = req.command

    # Checking if date is correct
    date: datetime.date = parse_date(res, date_str)

    if date is None:
        return

    # Additional check if any of the selected notes has this date
    async with NoteStorage(req.user_id) as db:
        note: List[Record] = await db.select_notes(req.user_data['title'], date)

    if len(note) == 0:
        res.send_message('Упс! По указанной дате ничего не нашлось. Попробуете ещё раз?')
        return

    ask_note_form(res)
    res.send_user_data({'date': date_str, 'title': req.user_data['title']})


@status_handler(DialogStatus.FIND_NOTE_FORM_INPUT)
async def find_note_form_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    res.send_user_data({'title': title})

    async with NoteStorage(req.user_id) as db:
        if 'date' not in req.user_data:
            note: List[Record] = await db.select_notes(title)
        else:
            date_str: str = req.user_data['date']

            res.send_user_data({'date': date_str})

            # At this point we've ensured that the date is fully correct and that the note does exist
            date: datetime.date = parse_date(res, date_str)

            note: List[Record] = await db.select_notes(title, date)

    confirm = 'YANDEX.CONFIRM' in req.nlu.intents or 'confirm' in req.nlu.intents
    reject = 'YANDEX.REJECT' in req.nlu.intents or 'reject' in req.nlu.intents
    if confirm:
        res.send_message(note[0][1])
    elif reject:
        res.send_message(note[0][0])
    else:
        res.send_message('Извините, не понял вас! Повторите, в какой форме вы хотите услышать заметку:'
                         ' краткой или полной?')
        res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)
