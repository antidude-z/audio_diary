from flask import Flask, request
from datetime import date
import psycopg2


app = Flask(__name__)


@app.route('/', methods=['POST'])
def main():
    req = request.json
    intent_id = req['request']['nlu']['intents']
    user_id = req['session']['user']['user_id']
    date_today = date.today()
    user_text = (req['request']['original_utterance']).lower()
    funk_1 = 'create_note'
    funk_2 = 'create_name'
    funk_3 = 'delete_note'

    conn = psycopg2.connect(dbname='my_users', user='postgres',        #соединяюсь с бд
                        password='2G5i7r1a6f3E', host='localhost')
    cursor = conn.cursor()  #получаю курсор
    cursor.execute("SELECT * FROM user_states WHERE user_id = %s", (user_id,))  #получаю строки, в которых указан id юзера
    records = cursor.fetchall()

    if len(records) != 3:  #проверяю есть ли у юзера вообще поля - если нет, добавляю их
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_1, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_2, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_3, False))

    if req['session']['new']:  #проверяю сессию: новая -> True, нет -> False
        response_text = 'Начало работы тестового навыка'
    else:
        if intent_id.get('new_note') != None:  #обрабатываю запрос пользователя
            response_text = 'Придумайте имя записи'
            cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_2))  #state = True (в бд)
        elif intent_id.get('del_note') != None:  #обрабатываю другой вариант запроса пользователя
            response_text = 'Запись, с каким названием, Вы бы хотели удалить?'
            cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_3))
        else:
            cursor.execute("SELECT funk, state FROM user_states WHERE user_id = %s", (user_id,))  #вытаскиваю из бд значение поля state
            for row in cursor.fetchall():
                if row == ('create_name', True):  #проверяю нужно ли создавать имя записи
                    cursor.execute("INSERT INTO users (note_date, note_name, user_id) VALUES (%s, %s, %s)", (date_today, user_text, user_id))
                    response_text = 'Имя заметки сохранено. Начало записи...'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_2))
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_1))
                elif row == ('create_note', True):  #проверяю нужно ли создавать запись
                    cursor.execute("SELECT note_name FROM users WHERE user_id = %s AND note_date = %s", (user_id, date_today))
                    records = cursor.fetchall()
                    for i in records[-1]:
                        name = i
                    cursor.execute("UPDATE users SET full_note = %s WHERE note_name = %s", (user_text, name))
                    response_text = 'Новая запись успешно добавлена!'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_1))
                elif row == ('delete_note', True):
                    cursor.execute("SELECT * FROM users WHERE note_name = %s AND user_id = %s", (user_text, user_id))
                    if len(cursor.fetchall()) > 0:
                        cursor.execute("DELETE FROM users WHERE note_name = %s AND user_id = %s", (user_text, user_id))
                        response_text = 'Запись успешно удалена!'
                    else:
                        response_text = 'У вас нет записи с таким названием'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_3))
                else:
                    response_text = 'Запрос не распознан'
    
    response = {
        'version': req['version'],
        'session': req['session'],
        'response': {
            'text': response_text,
            'end_session': False
            },
    }

    conn.commit() #сохраняю изменения
    cursor.close()  #закрываю курсор и соединение
    conn.close()
    return response

app.run('0.0.0.0', port=5000, debug=True)