"""A main module which handles Alice requests at core level and contains all dialog status handlers with most of the
skill functionality."""

import asyncio
import datetime
from typing import Dict, List

from aiohttp import web
from aiohttp.web_response import Response as AioResponse
from asyncpg import Record
import dateparser

from dialog_manager import DialogStatus, DialogRequest, DialogResponse, status_handler, get_handler, StatusHandlerType
from note_storage import NoteStorage
from summarize import create_short_note, start_scheduler, cleanup_scheduler


async def main(request: web.BaseRequest) -> AioResponse:
    """Handles '/' request from Alice."""

    request_data: Dict = await request.json()

    # Initialise Request and Response objects
    req: DialogRequest = DialogRequest(request_data)
    res: DialogResponse = DialogResponse()

    res.transfer_persistence(req)

    # Call an appropriate handler for current dialog status
    callback: StatusHandlerType = get_handler(req.status)
    response_data: Dict = await callback(req, res)
    return web.json_response(response_data)


@status_handler(DialogStatus.IDLE)
async def idle(req: DialogRequest, res: DialogResponse) -> None:
    """Basic handler for every request which has not been classified as anything else."""

    if req.is_new_session:
        res.send_message('Навык "Аудиодневник" запущен и готов к работе... (v1)')
    elif req.exit_current_status:
        res.send_message('Отменено.')
    else:
        res.send_message('Запрос не распознан.')


# Below are many self-explanatory handlers that go through various dialog scenarios step-by-step.

@status_handler(DialogStatus.NEW_NOTE)
async def new_note(req: DialogRequest, res: DialogResponse) -> None:
    res.send_status(DialogStatus.NEW_NOTE_TITLE_INPUT)
    res.send_message('Придумайте имя записи.')


@status_handler(DialogStatus.NEW_NOTE_TITLE_INPUT)
async def new_note_title_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.command
    date: datetime.date = datetime.date.today()

    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes(title, date)

    # We cannot create two notes with the same title and date. Thus, we send the user back to title input
    if len(notes) > 0:
        res.send_message('У вас уже есть заметка с таким названием, датированная сегодняшним днём. '
                         'Придумайте что-нибудь другое.')
        res.send_status(DialogStatus.NEW_NOTE_TITLE_INPUT)
    else:
        res.send_message('Имя заметки сохранено. Начало записи...')
        res.send_user_data({'title': title})
        res.send_status(DialogStatus.NEW_NOTE_TEXT_INPUT)


@status_handler(DialogStatus.NEW_NOTE_TEXT_INPUT)
async def new_note_text_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    full_note: str = req.user_input

    async with NoteStorage(req.user_id) as db:
        await db.insert_new_note(title, full_note)

    # Running short form creation in the background because it usually holds the request for >1 second (bad for UX)
    today: datetime.date = datetime.date.today()
    asyncio.create_task(create_short_note(full_note, req.user_id, title, today))

    res.send_message('Новая запись успешно добавлена!')


@status_handler(DialogStatus.DEL_NOTE)
async def del_note(req: DialogRequest, res: DialogResponse) -> None:
    res.send_message('Запись с каким названием Вы бы хотели удалить?')
    res.send_status(DialogStatus.DEL_NOTE_TITLE_INPUT)


@status_handler(DialogStatus.DEL_NOTE_TITLE_INPUT)
async def del_note_title_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.command

    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes(title)

        if len(notes) == 1:  # If title is unique, simply delete the corresponding note
            await db.delete_notes(title)
            res.send_message('Запись успешно удалена!')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            res.send_status(DialogStatus.DEL_NOTE_DATE_INPUT)
            res.send_user_data({'title': title})
            date_list: List[str] = [str(i[3]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день.")
        else:
            res.send_message('У вас нет записи с таким названием.')


@status_handler(DialogStatus.DEL_NOTE_DATE_INPUT)
async def del_note_date_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    date: datetime.date = dateparser.parse(req.command).date()

    async with NoteStorage(req.user_id) as db:
        await db.delete_notes(title, date)

    res.send_message('Запись успешно удалена!')


@status_handler(DialogStatus.FIND_NOTE)
async def find_note(req: DialogRequest, res: DialogResponse) -> None:
    if len(req.nlu_tokens) != 1:  # If user input contains any words after 'note', we assume them as a title
        title: str = ' '.join(req.nlu_tokens[1:])

        async with NoteStorage(req.user_id) as db:
            notes: List[Record] = await db.select_notes(title)

        if len(notes) == 1:  # If there is only one note, send it back to user
            res.send_message('Выберите форму записи. Краткая или полная?')
            res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)
            res.send_user_data({'title': title, 'selection_type': 'title_only'}, persistent=True)
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            date_list: List[str] = [str(i[3]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день.")
            res.send_status(DialogStatus.FIND_NOTE_DATE_INPUT)
            res.send_user_data({'title': title, 'selection_type': 'title_and_date'}, persistent=True)
        else:
            res.send_message('Нет записи с таким названием')
    else:
        res.send_message('Вы не указали имя заметки')


@status_handler(DialogStatus.FIND_NOTE_DATE_INPUT)
async def find_note_date_input(req: DialogRequest, res: DialogResponse) -> None:
    date_str: str = req.command

    res.send_message('Выберите форму записи. Краткая или полная?')
    res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)
    res.send_user_data({'date': date_str})


@status_handler(DialogStatus.FIND_NOTE_FORM_INPUT)
async def find_note_form_input(req: DialogRequest, res: DialogResponse) -> None:
    title: str = req.user_data['title']
    selection_type: str = req.user_data['selection_type']

    res.drop_persistent_user_data('title', 'selection_type')

    async with NoteStorage(req.user_id) as db:
        if selection_type == 'title_only':
            note: List[Record] = await db.select_notes(title)
        elif selection_type == 'title_and_date':
            date_str: str = req.user_data['date']
            date: datetime.date = dateparser.parse(date_str).date()
            note: List[Record] = await db.select_notes(title, date)

    # TODO: rework with intents
    if req.command == 'краткая':
        res.send_message(note[0][1])
    elif req.command == 'полная':
        res.send_message(note[0][0])


@status_handler(DialogStatus.LIST_ALL_NOTES)
async def list_all_notes(req: DialogRequest, res: DialogResponse) -> None:
    async with NoteStorage(req.user_id) as db:
        notes: List[Record] = await db.select_notes()

    res.send_message('У вас сохранены следующие заметки:\n')
    for note in notes:
        title, date = note[2], note[3]
        res.send_message(f"- '{title}' от {date}")


# Running in HTTP on dev server only, HTTPS connection is currently established through Cloudpub
app: web.Application = web.Application()
app.add_routes([web.post('/', main)])
app.on_startup.append(start_scheduler)
app.on_cleanup.append(cleanup_scheduler)
web.run_app(app, port=5000)
