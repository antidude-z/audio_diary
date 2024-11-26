import os
import datetime
import dateparser
import asyncio
from summarize import summarize
from aiohttp import web
from dialog_manager import DialogStatus, DialogRequest, DialogResponse, status_handler, get_callback
from note_storage import NoteStorage

#TODO: note_id?

NoteStorage.setup(db_user=os.getenv('DBUSER'), password=os.getenv('DBPASSWORD'), host=os.getenv('DBHOST'))

async def main(request: web.BaseRequest):
    request_data = await request.json()

    # Initialise Request and Response objects
    req = DialogRequest(request_data)
    res = DialogResponse(request_data)

    # If 'user_data' entry name starts with underscore, it's automatically sent to the next request
    for name, value in req.user_data.items():
        if name[0] == '_':
            res.send_user_data(name, value)

    # Calling an appropriate handler for current dialog status
    callback = get_callback(req.status)
    response_data = await callback(req, res)
    return web.json_response(response_data)

@status_handler(DialogStatus.IDLE)
async def idle(req: DialogRequest, res: DialogResponse):
    if req.is_new_session:
        res.send_message('Начало работы тестового навыка')
    elif req.exit_current_status:
        res.send_message('Отменено')
    else:
        res.send_message('Запрос не распознан')

@status_handler(DialogStatus.NEW_NOTE)
async def new_note(req: DialogRequest, res: DialogResponse):
    res.send_status(DialogStatus.INPUT_TITLE)
    res.send_message('Придумайте имя записи')

@status_handler(DialogStatus.INPUT_TITLE)
async def input_name(req: DialogRequest, res: DialogResponse):
    title = req.command
    date = datetime.date.today()
    async with NoteStorage(req.user_id) as db:
        notes = await db.execute('select_note', (title, date))

    # We cannot create two notes with the same title and date. Thus, we send the user back to title input stage
    if len(notes) > 0:
        res.send_message('У вас уже есть заметка с таким названием, датированная сегодняшним днём. '
                         'Придумайте что-нибудь другое')
        res.send_status(DialogStatus.INPUT_TITLE)
    else:
        res.send_message('Имя заметки сохранено. Начало записи...')
        res.send_user_data('new_note_title', title)
        res.send_status(DialogStatus.INPUT_NOTE)

@status_handler(DialogStatus.INPUT_NOTE)
async def input_note(req: DialogRequest, res: DialogResponse):
    async with NoteStorage(req.user_id) as db:
        title = req.user_data['new_note_title']
        date = datetime.date.today()
        full_note = req.user_input
        asyncio.create_task(summarize(full_note, req.user_id, title, date))
        await db.execute("add_note", (title, date, full_note, "0"))

    res.send_message('Новая запись успешно добавлена!')

@status_handler(DialogStatus.DELETE_NOTE)
async def delete_note(req: DialogRequest, res: DialogResponse):
    res.send_message('Запись с каким названием Вы бы хотели удалить?')
    res.send_status(DialogStatus.INPUT_DEL_NOTE)

@status_handler(DialogStatus.INPUT_DEL_NOTE)
async def input_del_note(req: DialogRequest, res: DialogResponse):
    title = req.command

    async with NoteStorage(req.user_id) as db:
        notes = await db.execute("select_all_notes_by_title", title)

        if len(notes) == 1:  # If title is unique, simply delete the corresponding note
            await db.execute('delete_note', title)
            res.send_message('Запись успешно удалена!')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            res.send_status(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
            res.send_user_data('delete_note_title', title)
            date_list = [str(i[2]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день")
        else:
            res.send_message('У вас нет записи с таким названием')

@status_handler(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
async def input_del_note_by_date(req: DialogRequest, res: DialogResponse):
    async with NoteStorage(req.user_id) as db:
        title = req.user_data['delete_note_title']
        date = dateparser.parse(req.command).date()
        await db.execute('delete_note_by_date', (title, date))
    res.send_message('Запись успешно удалена!')

@status_handler(DialogStatus.FIND_NOTE)
async def find_note(req: DialogRequest, res: DialogResponse):
    if len(req.nlu_tokens) != 1:  # If user input contains any words after 'note', we assume them as a title
        title = ' '.join(req.nlu_tokens[1:])

        async with NoteStorage(req.user_id) as db:
            notes = await db.execute("select_all_notes_by_title", title)

        if len(notes) == 1:  # If there is only one note, send it back to user
            res.send_message('Выберите форму записи. Краткая или полная?')
            res.send_status(DialogStatus.SELECT_FORM)
            res.send_user_data('select_form_title', title)
            res.send_user_data('select_form_type', 'title_only')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            date_list = [str(i[2]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день")
            res.send_status(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
            res.send_user_data('find_note_title', title)
        else:
            res.send_message('Нет записи с таким названием')
    else:
        res.send_message('Вы не указали имя заметки')

@status_handler(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
async def input_find_note_by_date(req: DialogRequest, res: DialogResponse):
    title = req.user_data['find_note_title']

    res.send_message('Выберите форму записи. Краткая или полная?')
    res.send_status(DialogStatus.SELECT_FORM)
    res.send_user_data('select_form_title', title)
    res.send_user_data('select_form_date', req.command)
    res.send_user_data('select_form_type', 'title_and_date')

@status_handler(DialogStatus.SELECT_FORM)
async def select_form(req: DialogRequest, res: DialogResponse):
    title = req.user_data['select_form_title']
    selection_type = req.user_data['select_form_type']
    async with NoteStorage(req.user_id) as db:
        if selection_type == 'title_only':
            notes = await db.execute('select_all_notes_by_title', title)
        elif selection_type == 'title_and_date':
            date = dateparser.parse(req.user_data['select_form_date']).date()
            notes = await db.execute('select_note', (title, date))

    #TODO: rework with intents
    if req.command == 'краткая':
        res.send_message(notes[0][1])
    elif req.command == 'полная':
        res.send_message(notes[0][0])

@status_handler(DialogStatus.LIST_ALL_NOTES)
async def list_all_notes(req: DialogRequest, res: DialogResponse):
    async with NoteStorage(req.user_id) as db:
        notes = await db.execute("select_all_notes")

    res.send_message('У вас сохранены следующие заметки:\n')
    for note in notes:
        name, date = note
        res.send_message(f"- '{name}' от {date}")

# Running in HTTPS on remote server only, otherwise secure connection is established through Cloudpub
if os.getenv('DBHOST') == 'localhost':
    # app.run('0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
    pass
else:
    app = web.Application()
    app.add_routes([web.post('/', main)])
    web.run_app(app, port=5000)
    # app.run('0.0.0.0', port=5000, debug=True)
