import datetime
from typing import List, Optional

from asyncpg import Record

from dialog_manager import DialogRequest, DialogResponse, DialogStatus, status_handler, Intent, EntityString
from note_storage import NoteStorage
from util import send_date_list, parse_date


async def deletion_attempt_by_title(req: DialogRequest, res: DialogResponse, title: str):
    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes(title)

        if len(notes) == 1:  # If title is unique, simply delete the corresponding note
            await db.delete_notes(title)
            res.send_message('Запись успешно удалена!')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            res.send_status(DialogStatus.DEL_NOTE_DATE_INPUT)
            res.send_user_data({'title': title})
            send_date_list(res, notes)
        else:
            res.send_message('У вас нет записи с таким названием.')


@status_handler(DialogStatus.DEL_NOTE)
async def del_note(req: DialogRequest, res: DialogResponse) -> None:
    intent: Intent = req.nlu.intents['del_note']

    title: Optional[EntityString] = intent.slots.get('title')
    date: Optional[EntityString] = intent.slots.get('date')

    if title is not None and date is not None:
        date_object = parse_date(res, date.value)

        if date_object is None:
            return

        async with NoteStorage(req.user_id) as db:
            note = await db.select_notes(title.value, date_object)
            if len(note) != 0:
                await db.delete_notes(title.value, date_object)
                res.send_message('Запись успешно удалена!')
            else:
                res.send_message('Извините, не нашёл такой заметки. Попробуйте снова.')
    elif title is not None:
        await deletion_attempt_by_title(req, res, title.value)
    else:
        res.send_message('Запись с каким названием Вы бы хотели удалить?')
        res.send_status(DialogStatus.DEL_NOTE_TITLE_INPUT)


@status_handler(DialogStatus.DEL_NOTE_TITLE_INPUT)
async def del_note_title_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.command

    await deletion_attempt_by_title(req, res, title)


@status_handler(DialogStatus.DEL_NOTE_DATE_INPUT)
async def del_note_date_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    date: datetime.date = parse_date(res, req.command)

    if date is None:
        return

    async with NoteStorage(req.user_id) as db:
        await db.delete_notes(title, date)

    res.send_message('Запись успешно удалена!')
