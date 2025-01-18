import asyncio
import datetime
from typing import List

from asyncpg import Record

from dialog_manager import status_handler, DialogStatus, DialogRequest, DialogResponse, Intent
from note_storage import NoteStorage
from summarize import create_short_note


async def start_note_creation(req: DialogRequest, res: DialogResponse, title, date, text):
    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes(title, date)

    # We cannot create two notes with the same title and date. Thus, we send the user back to title input
    if len(notes) > 0:
        res.send_message('У вас уже есть заметка с таким названием, записанная сегодня. Придумайте что-нибудь другое.')
    else:
        res.send_message('Название сохранено. Слушаю вас!')
        res.send_user_data({'title': title})
        res.send_status(DialogStatus.NEW_NOTE_TEXT_INPUT)


@status_handler(DialogStatus.NEW_NOTE)
async def new_note(req: DialogRequest, res: DialogResponse) -> None:
    intent: Intent = req.nlu.intents.get('new_note')
    date: datetime.date = datetime.date.today()

    if 'title' not in intent.slots:
        res.send_status(DialogStatus.NEW_NOTE_TITLE_INPUT)
        res.send_message('Назовите имя вашей записи.')
    else:
        await start_note_creation(req, res, intent.slots['title'].value, date, 'Начинаю запись!')


@status_handler(DialogStatus.NEW_NOTE_TITLE_INPUT)
async def new_note_title_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.command
    date: datetime.date = datetime.date.today()

    await start_note_creation(req, res, title, date, 'Название сохранено. Слушаю вас!')


@status_handler(DialogStatus.NEW_NOTE_TEXT_INPUT)
async def new_note_text_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    full_note: str = req.user_input

    async with NoteStorage(req.user_id) as db:
        await db.insert_new_note(title, full_note)

    # Running short form creation in the background because it usually holds the request for >1 second (bad for UX)
    today: datetime.date = datetime.date.today()
    asyncio.create_task(create_short_note(full_note, req.user_id, title, today))

    res.send_message('Новая заметка успешно добавлена!')
