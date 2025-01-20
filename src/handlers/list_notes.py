from typing import List

from asyncpg import Record

from dialog_manager import DialogRequest, DialogResponse, DialogStatus, status_handler
from note_storage import NoteStorage
from util import transform_date


async def pretty_print_notes(res: DialogResponse, notes: List) -> None:
    for note in notes:
        title, date = note[2], transform_date(note[3])
        res.send_message(f"«{title}» от {date}")


@status_handler(DialogStatus.LIST_ALL_NOTES)
async def list_all_notes(req: DialogRequest, res: DialogResponse) -> None:
    if 'list_all_notes' in req.nlu.intents:
        page = 0
    else:
        page = req.user_data.get('page')

    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = (await db.select_notes())[::-1]
        notes.sort(key=lambda x: x[3], reverse=True)

    if len(notes) == 0:
        res.send_message('У вас не сохранено ни одной заметки. Добавьте новую по команде "новая запись".')
        return
    elif len(notes) <= 3:
        res.send_message('У вас сохранены следующие заметки:\n')
        await pretty_print_notes(res, notes)
    else:
        if page == 0:
            res.send_message('Ваши недавние заметки:')
        await pretty_print_notes(res, notes[page * 3: (page + 1) * 3])
        if len(notes) > (page + 1) * 3:
            res.send_message('Для получения более старых заметок скажите "далее".')
            res.send_user_data({'page': page + 1})


@status_handler(DialogStatus.LIST_NEXT)
async def list_next(req: DialogRequest, res: DialogResponse) -> None:
    if req.user_data.get('page') is not None:
        await list_all_notes(req, res)
    else:
        res.send_message('Извините, не понял Вас. Попробуйте переформулировать запрос или попросите меня помочь.')
