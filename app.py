import os
import datetime
from flask import Flask, request
from dialog_manager import DialogStatus, DialogRequest, DialogResponse, status_handler, get_callback
from note_storage import NoteStorage

app = Flask(__name__)
NoteStorage.setup(db_user=os.getenv('DBUSER'), password=os.getenv('DBPASSWORD'), host=os.getenv('DBHOST'))

@app.route('/', methods=['POST'])
def main():
    # Initialise Request and Response objects
    req = DialogRequest(request.json)
    res = DialogResponse(request.json)

    # If 'user_data' entry name starts with underscore, it's automatically sent to the next request
    for name, value in req.user_data.items():
        if name[0] == '_':
            res.send_user_data(name, value)

    # Calling an appropriate handler for current dialog status
    callback = get_callback(req.status)
    return callback(req, res)

@status_handler(DialogStatus.IDLE)
def idle(req: DialogRequest, res: DialogResponse):
    if req.is_new_session:
        res.send_message('Начало работы тестового навыка')
    else:
        res.send_message('Запрос не распознан')

@status_handler(DialogStatus.NEW_NOTE)
def new_note(req: DialogRequest, res: DialogResponse):
    res.send_status(DialogStatus.INPUT_NAME)
    res.send_message('Придумайте имя записи')

@status_handler(DialogStatus.INPUT_NAME)
def input_name(req: DialogRequest, res: DialogResponse):
    res.send_message('Имя заметки сохранено. Начало записи...')
    res.send_user_data('new_note_title', req.user_input)
    res.send_status(DialogStatus.INPUT_NOTE)

@status_handler(DialogStatus.INPUT_NOTE)
def input_note(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        title = req.user_data['new_note_title']
        date = datetime.date.today()
        full_note = req.user_input
        db.execute("add_note", (title, date, full_note))

    res.send_message('Новая запись успешно добавлена!')

@status_handler(DialogStatus.DELETE_NOTE)
def delete_note(req: DialogRequest, res: DialogResponse):
    res.send_message('Запись с каким названием Вы бы хотели удалить?')
    res.send_status(DialogStatus.INPUT_DEL_NOTE)

@status_handler(DialogStatus.INPUT_DEL_NOTE)
def input_del_note(req: DialogRequest, res: DialogResponse):
    title = req.user_input

    with NoteStorage(req.user_id) as db:
        notes = db.execute("select_all_notes_by_title", title)

        if len(notes) == 1:  # If title is unique, simply delete the corresponding note
            db.execute('delete_note', title)
            res.send_message('Запись успешно удалена!')
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            res.send_status(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
            res.send_user_data('delete_note_title', title)
            date_list = [str(i[1]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день")
        else:
            res.send_message('У вас нет записи с таким названием')

@status_handler(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
def input_del_note_by_date(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        title = req.user_data['delete_note_title']
        date = datetime.datetime.strptime(req.user_input, '%Y-%m-%d').date()
        db.execute('delete_note_by_date', (title, date))
    res.send_message('Запись успешно удалена!')

@status_handler(DialogStatus.FIND_NOTE)
def find_note(req: DialogRequest, res: DialogResponse):
    if len(req.nlu_tokens) != 1:  # If user input contains any words after 'note', we assume them as a title
        title = ' '.join(req.nlu_tokens[1:])

        with NoteStorage(req.user_id) as db:
            notes = db.execute("select_all_notes_by_title", title)

        if len(notes) == 1:  # If there is only one note, send it back to user
            res.send_message(notes[0][0])
        elif len(notes) > 1:  # If there are few notes with the same title, ask user to specify the date
            date_list = [str(i[1]) for i in notes]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. "
                             f"Выберите интересующий Вас день")
            res.send_status(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
            res.send_user_data('find_note_title', title)
        else:
            res.send_message('Нет записи с таким названием')
    else:
        res.send_message('Вы не указали имя заметки')

@status_handler(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
def input_find_note_by_date(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        title = req.user_data['find_note_title']
        date = datetime.datetime.strptime(req.user_input, '%Y-%m-%d').date()
        note = db.execute('select_note', (title, date))[0][0]

    res.send_message(note)

@status_handler(DialogStatus.LIST_ALL_NOTES)
def list_all_notes(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        notes = db.execute("select_all_notes")

    res.send_message('У вас сохранены следующие заметки:\n')
    for note in notes:
        name, date = note
        res.send_message(f"- '{name}' от {date}")

# Running in HTTPS on remote server only, otherwise secure connection is established through Cloudpub
if os.getenv('DBHOST') == 'localhost':
    app.run('0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
else:
    app.run('0.0.0.0', port=5000, debug=True)
