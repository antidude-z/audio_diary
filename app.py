import os
from dialog_manager import *
from flask import Flask, request
from note_storage import NoteStorage

app = Flask(__name__)
NoteStorage.setup(user=os.getenv('DBUSER'), password=os.getenv('DBPASSWORD'), host=os.getenv('DBHOST'))

@app.route('/', methods=['POST'])
def main():
    req: dict = request.json
    session_storage = SessionStorage(req)
    func = response_functions[session_storage.dialog_status]

    return func(session_storage)

@status(DialogStatus.IDLE)
def idle(st: SessionStorage):
    if st.is_new_session:
        st.respond_text('Начало работы тестового навыка')
    else:
        st.respond_text('Запрос не распознан')

@status(DialogStatus.NEW_NOTE)
def new_note(st: SessionStorage):
    st.respond_dialog_status(DialogStatus.INPUT_NAME)
    st.respond_text('Придумайте имя записи')

@status(DialogStatus.INPUT_NAME)
def input_name(st: SessionStorage):
    st.respond_text('Имя заметки сохранено. Начало записи...')
    st.respond_user_data('new_note_name', st.user_text)
    st.respond_dialog_status(DialogStatus.INPUT_NOTE)

@status(DialogStatus.INPUT_NOTE)
def input_note(st: SessionStorage):
    ns = NoteStorage(st.user_id)
    ns.add_note(st['new_note_name'], st.user_text)
    st.respond_text('Новая запись успешно добавлена!')
    ns.close_connection()

@status(DialogStatus.DELETE_NOTE)
def delete_note(st: SessionStorage):
    st.respond_text('Запись с каким названием Вы бы хотели удалить?')
    st.respond_dialog_status(DialogStatus.INPUT_DEL_NOTE)

@status(DialogStatus.INPUT_DEL_NOTE)
def input_del_note(st: SessionStorage):
    note_storage = NoteStorage(st.user_id)
    records = note_storage.select_all_notes_by_name(st.user_text)

    if len(records) == 1:  # если запись всего одна
        note_storage.delete_note(st.user_text)
        st.respond_text('Запись успешно удалена!')
    elif len(records) > 1:  # если несколько записей с одинаковым названием
        st.respond_dialog_status(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
        st.respond_user_data('note_for_deletion', st.user_text)
        date_list = [str(i[1]) for i in records]
        st.respond_text(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберите интересующий Вас день")
    else:
        st.respond_text('У вас нет записи с таким названием')

    note_storage.close_connection()

@status(DialogStatus.INPUT_DEL_NOTE_BY_DATE)
def input_del_note_by_date(st: SessionStorage):
    note_storage = NoteStorage(st.user_id)
    note_storage.delete_note(st['note_for_deletion'], st.user_text)
    st.respond_text('Запись успешно удалена!')
    note_storage.close_connection()

@status(DialogStatus.FIND_NOTE)
def find_note(st: SessionStorage):
    note_storage = NoteStorage(st.user_id)

    if len(st.tokens) != 1:  # проверяю сколько слов ввел пользователь
        find_name = ' '.join(st.tokens[1::])
        records = note_storage.select_all_notes_by_name(find_name)

        if len(records) == 1:
            st.respond_text(records[0][0])
        elif len(records) == 0:
            st.respond_text('Нет записи с таким названием')
        else:
            date_list = [str(i[1]) for i in records]
            st.respond_text(f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберете интересующий Вас день")
            st.respond_dialog_status(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
            st.respond_user_data('note_for_search', find_name)
    else:
        st.respond_text('Вы не указали имя заметки')

    note_storage.close_connection()

@status(DialogStatus.INPUT_FIND_NOTE_BY_DATE)
def input_find_note_by_date(st: SessionStorage):
    note_storage = NoteStorage(st.user_id)
    note = note_storage.select_note(st['note_for_search'], st.user_text)
    st.respond_text(note)
    note_storage.close_connection()

if os.getenv('DBHOST') == 'localhost':
    app.run('0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
else:
    app.run('0.0.0.0', port=5000, debug=True)
