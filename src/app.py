import datetime
import dateparser
import asyncio
from summarize import create_short_note, start_scheduler, cleanup_scheduler
from aiohttp import web
from dialog_manager import DialogStatus, DialogRequest, DialogResponse, status_handler, get_callback
from note_storage import NoteStorage

#TODO: queries and note_id rework?

async def main(request: web.BaseRequest):
    request_data = await request.json()

    # Initialise Request and Response objects
    req = DialogRequest(request_data)
    res = DialogResponse.from_request(req)

    # Calling an appropriate handler for current dialog status
    callback = get_callback(req.status)
    response_data = await callback(req, res)
    return web.json_response(response_data)

@status_handler(DialogStatus.IDLE)
async def idle(req: DialogRequest, res: DialogResponse):
    if req.is_new_session:
        res.send_message('Навык "Аудиодневник" запущен и готов к работе...')
    elif req.exit_current_status:
        res.send_message('Отменено.')
    else:
        res.send_message('Запрос не распознан.')

@status_handler(DialogStatus.NEW_NOTE)
async def new_note(req: DialogRequest, res: DialogResponse):
    res.send_status(DialogStatus.NEW_NOTE_TITLE_INPUT)
    res.send_message('Придумайте имя записи.')

@status_handler(DialogStatus.NEW_NOTE_TITLE_INPUT)
async def new_note_title_input(req: DialogRequest, res: DialogResponse):
    title = req.command
    date = datetime.date.today()
    
    async with NoteStorage(req.user_id) as db:
        notes = await db.execute('select_note', (title, date))

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
async def new_note_text_input(req: DialogRequest, res: DialogResponse):
    title = req.user_data['title']
    date = datetime.date.today()
    full_note = req.user_input
    
    async with NoteStorage(req.user_id) as db:
        await db.execute("insert_full_note", (title, date, full_note))

    # Running short note creation in the background because it usually holds the request for >1 second (bad for UX)
    asyncio.create_task(create_short_note(full_note, req.user_id, title, date))

    res.send_message('Новая запись успешно добавлена!')

@status_handler(DialogStatus.DEL_NOTE)
async def del_note(req: DialogRequest, res: DialogResponse):
    res.send_message('Запись с каким названием Вы бы хотели удалить?')
    res.send_status(DialogStatus.DEL_NOTE_TITLE_INPUT)

@status_handler(DialogStatus.DEL_NOTE_TITLE_INPUT)
async def del_note_title_input(req: DialogRequest, res: DialogResponse):
    title = req.command

    async with NoteStorage(req.user_id) as db:
        notes = await db.execute("select_notes_by_title", title)

        if len(notes) == 1:  # If title is unique, simply delete the corresponding note
            await db.execute('delete_note_by_title', title)
            res.send_message('Запись успешно удалена!')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            res.send_status(DialogStatus.DEL_NOTE_DATE_INPUT)
            res.send_user_data({'title': title})
            date_list = [str(i[2]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день.")
        else:
            res.send_message('У вас нет записи с таким названием.')

@status_handler(DialogStatus.DEL_NOTE_DATE_INPUT)
async def del_note_date_input(req: DialogRequest, res: DialogResponse):
    title = req.user_data['title']
    date = dateparser.parse(req.command).date()

    async with NoteStorage(req.user_id) as db:
        await db.execute('delete_note', (title, date))

    res.send_message('Запись успешно удалена!')

@status_handler(DialogStatus.FIND_NOTE)
async def find_note(req: DialogRequest, res: DialogResponse):
    if len(req.nlu_tokens) != 1:  # If user input contains any words after 'note', we assume them as a title
        title = ' '.join(req.nlu_tokens[1:])

        async with NoteStorage(req.user_id) as db:
            notes = await db.execute("select_notes_by_title", title)

        if len(notes) == 1:  # If there is only one note, send it back to user
            res.send_message('Выберите форму записи. Краткая или полная?')
            res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)
            res.send_user_data({'title': title, 'selection_type': 'title_only'}, persistent=True)
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            date_list = [str(i[2]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день.")
            res.send_status(DialogStatus.FIND_NOTE_DATE_INPUT)
            res.send_user_data({'title': title, 'selection_type': 'title_and_date'}, persistent=True)
        else:
            res.send_message('Нет записи с таким названием')
    else:
        res.send_message('Вы не указали имя заметки')

@status_handler(DialogStatus.FIND_NOTE_DATE_INPUT)
async def find_note_date_input(req: DialogRequest, res: DialogResponse):
    date_str = req.command

    res.send_message('Выберите форму записи. Краткая или полная?')
    res.send_status(DialogStatus.FIND_NOTE_FORM_INPUT)
    res.send_user_data({'date': date_str})

@status_handler(DialogStatus.FIND_NOTE_FORM_INPUT)
async def find_note_form_input(req: DialogRequest, res: DialogResponse):
    title = req.user_data['title']
    selection_type = req.user_data['selection_type']

    res.drop_persistent_user_data('title', 'selection_type')

    async with NoteStorage(req.user_id) as db:
        if selection_type == 'title_only':
            note = await db.execute('select_notes_by_title', title)
        elif selection_type == 'title_and_date':
            date_str = req.user_data['date']
            date = dateparser.parse(date_str).date()
            note = await db.execute('select_note', (title, date))

    #TODO: rework with intents + [0]
    if req.command == 'краткая':
        res.send_message(note[0][1])
    elif req.command == 'полная':
        res.send_message(note[0][0])

@status_handler(DialogStatus.LIST_ALL_NOTES)
async def list_all_notes(req: DialogRequest, res: DialogResponse):
    async with NoteStorage(req.user_id) as db:
        notes = await db.execute("select_all_notes")

    res.send_message('У вас сохранены следующие заметки:\n')
    for note in notes:
        name, date = note
        res.send_message(f"- '{name}' от {date}")

# Running in HTTPS on remote server only, otherwise secure connection is established through Cloudpub
app = web.Application()
app.add_routes([web.post('/', main)])
app.on_startup.append(start_scheduler)
app.on_cleanup.append(cleanup_scheduler)
web.run_app(app, port=5000)
