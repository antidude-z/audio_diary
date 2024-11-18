import os
from flask import Flask, request
from dialog_manager import DialogStatus, DialogRequest, DialogResponse, status_handler, get_callback
from note_storage import NoteStorage

app = Flask(__name__)
NoteStorage.setup(user=os.getenv('DBUSER'), password=os.getenv('DBPASSWORD'), host=os.getenv('DBHOST'))

@app.route('/', methods=['POST'])
def main():
    req = DialogRequest(request.json)
    res = DialogResponse(request.json)

    for name, value in req.user_data.items():
        if name[0] == '_':
            res.send_user_data(name, value)

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
    res.send_user_data('new_note_name', req.user_input)
    res.send_status(DialogStatus.INPUT_NOTE)

@status_handler(DialogStatus.INPUT_NOTE)
def input_note(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        db.add_note(req.user_data['new_note_name'], req.user_input)
    res.send_message('Новая запись успешно добавлена!')

@status_handler(DialogStatus.DELETE_NOTE)
def delete_note(req: DialogRequest, res: DialogResponse):
    res.send_message('Запись с каким названием Вы бы хотели удалить?')
    res.send_status(DialogStatus.INPUT_DEL_NOTE)

@status_handler(DialogStatus.INPUT_DEL_NOTE)
def input_del_note(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        records = db.select_all_notes_by_name(req.user_input)

        if len(records) == 1:  # если запись всего одна
            db.delete_note(req.user_input)
            res.send_message('Запись успешно удалена!')
        elif len(records) > 1:  # если несколько записей с одинаковым названием
            res.send_status(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
            res.send_user_data('note_for_deletion', req.user_input)
            date_list = [str(i[1]) for i in records]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберите интересующий Вас день")
        else:
            res.send_message('У вас нет записи с таким названием')

@status_handler(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
def input_del_note_by_date(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        db.delete_note(req.user_data['note_for_deletion'], req.user_input)
    res.send_message('Запись успешно удалена!')

@status_handler(DialogStatus.FIND_NOTE)
def find_note(req: DialogRequest, res: DialogResponse):
    if len(req.nlu_tokens) != 1:  # проверяю сколько слов ввел пользователь
        find_name = ' '.join(req.nlu_tokens[1::])

        with NoteStorage(req.user_id) as db:
            records = db.select_all_notes_by_name(find_name)

        if len(records) == 1:
            res.send_message(records[0][0])
        elif len(records) == 0:
            res.send_message('Нет записи с таким названием')
        else:
            date_list = [str(i[1]) for i in records]
            res.send_message(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберите интересующий Вас день")
            res.send_status(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
            res.send_user_data('note_for_search', find_name)
    else:
        res.send_message('Вы не указали имя заметки')

@status_handler(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
def input_find_note_by_date(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        note = db.select_note(req.user_data['note_for_search'], req.user_input)
    res.send_message(note)

@status_handler(DialogStatus.LIST_ALL_NOTES)
def list_all_notes(req: DialogRequest, res: DialogResponse):
    with NoteStorage(req.user_id) as db:
        records = db.select_all_notes()

    res.send_message('У вас сохранены следующие заметки:')
    for note in records:
        name, date = note
        res.send_message(f'{name} от {date}')

if os.getenv('DBHOST') == 'localhost':
    app.run('0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
else:
    app.run('0.0.0.0', port=5000, debug=True)
