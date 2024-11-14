import os
from flask import Flask, request
from note_storage import NoteStorage


app = Flask(__name__)
NoteStorage.setup(user=os.getenv('DBUSER'), password=os.getenv('DBPASSWORD'), host=os.getenv('DBHOST'))

@app.route('/', methods=['POST'])
def main():
    req: dict = request.json
    intent_id = req['request']['nlu']['intents']
    user_id = req['session']['user']['user_id']
    user_text = (req['request']['original_utterance']).lower()

    # вынести в enum?
    funk_1 = 'create_note'
    funk_2 = 'create_name'
    funk_3 = 'delete_note'
    funk_4 = 'find_note'
    funk_5 = 'delete_note_by_date'

    state_storage = req['state']
    response_state = {}

    note_storage = NoteStorage(user_id)

    if len(state_storage.get('session')) == 0:  #проверяю есть ли у юзера вообще поля - если нет, добавляю их
        response_state['dialog_status'] = 'idle'
    else:
        state_storage = state_storage['session']
        print(state_storage)

    if req['session']['new']:  #проверяю сессию: новая -> True, нет -> False
        response_text = 'Начало работы тестового навыка'
    else:
        if intent_id.get('new_note') != None:  #обрабатываю запрос пользователя
            response_text = 'Придумайте имя записи'
            response_state['dialog_status'] = 'create_name'
        elif intent_id.get('del_note') != None:  #обрабатываю другой вариант запроса пользователя
            response_text = 'Запись, с каким названием, Вы бы хотели удалить?'
            response_state['dialog_status'] = 'delete_note'
        elif intent_id.get('find_note') != None:
            if len(req['request']['nlu']['tokens']) != 1:  #проверяю сколько слов ввел пользователь
                find_name = ' '.join(req['request']['nlu']['tokens'][1::])
                records = note_storage.select_all_notes_by_name(find_name)
                if len(records) == 1:
                    response_text = records[0][0]  
                elif len(records) == 0:
                    response_text = 'Нет записи с таким названием'
                else:
                    date_list = [str(i[1]) for i in records]
                    response_text = f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберете интересующий Вас день"
                    response_state['dialog_status'] = 'find_note'
                    response_state['note_for_search'] = find_name
            else:
                response_text = 'Вы не указали имя заметки'
        else:
            if state_storage['dialog_status'] == 'create_name':  #проверяю нужно ли создавать имя записи
                response_state['new_note_name'] = user_text
                response_text = 'Имя заметки сохранено. Начало записи...'
                response_state['dialog_status'] = 'create_note'
            elif state_storage['dialog_status'] == 'create_note':  #проверяю нужно ли создавать запись
                note_storage.add_note(state_storage['new_note_name'], user_text)
                response_text = 'Новая запись успешно добавлена!'
                response_state['dialog_status'] = 'idle'
            elif state_storage['dialog_status'] == 'delete_note':  #проверяю нужно ли удалять запись
                records = note_storage.select_all_notes_by_name(user_text)
                response_state['dialog_status'] = 'idle'
                if len(records) == 1:  #если запись всего одна
                    note_storage.delete_note_by_name_only(user_text)
                    response_text = 'Запись успешно удалена!'
                elif len(records) > 1:  #если несколько записей с одинаковым названием
                    response_state['dialog_status'] = 'delete_note_by_date'
                    response_state['note_for_deletion'] = user_text
                    date_list = [str(i[1]) for i in records]
                    response_text = f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберите интересующий Вас день"
                else:
                    response_text = 'У вас нет записи с таким названием'
            elif state_storage['dialog_status'] == 'find_note':  #ищет запись с определенным названием
                note_date = user_text
                response_text = note_storage.select_note(state_storage['note_for_search'], note_date)
                response_state['dialog_status'] = 'idle'
            elif state_storage['dialog_status'] == 'delete_note_by_date':  #удаляет запись по дате, если записей несколько
                note_date = user_text
                note_storage.delete_note(state_storage['note_for_deletion'], note_date)
                response_text = 'Запись успешно удалена!'
                response_state['dialog_status'] = 'idle'
            else:
                response_text = 'Запрос не распознан'
    
    response = {
        'version': req['version'],
        'session': req['session'],
        'response': {
            'text': response_text,
            'end_session': False
        },
        'session_state': response_state
    }

    note_storage.close()
    return response

if os.getenv('DBHOST') == 'localhost':
    app.run('0.0.0.0', port=5000, debug=True, ssl_context=('cert.pem', 'key.pem'))
else:
    app.run('0.0.0.0', port=5000, debug=True)
