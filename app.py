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
    funk_4 = 'find_note'
    funk_5 = 'delete_note_by_date'

    conn = psycopg2.connect(dbname='my_users', user='postgres',        #соединяюсь с бд
                        password='2G5i7r1a6f3E', host='localhost')
    cursor = conn.cursor()  #получаю курсор
    cursor.execute("SELECT * FROM user_states WHERE user_id = %s", (user_id,))  #получаю строки, в которых указан id юзера
    records = cursor.fetchall()

    if len(records) != 5:  #проверяю есть ли у юзера вообще поля - если нет, добавляю их
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_1, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_2, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_3, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_4, False))
        cursor.execute("INSERT INTO user_states (user_id, funk, state) VALUES (%s, %s, %s)", (user_id, funk_5, False))

    if req['session']['new']:  #проверяю сессию: новая -> True, нет -> False
        response_text = 'Начало работы тестового навыка'
    else:
        if intent_id.get('new_note') != None:  #обрабатываю запрос пользователя
            response_text = 'Придумайте имя записи'
            cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_2))  #state = True (в бд)
        elif intent_id.get('del_note') != None:  #обрабатываю другой вариант запроса пользователя
            response_text = 'Запись, с каким названием, Вы бы хотели удалить?'
            cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_3))
        elif intent_id.get('find_note') != None:
            if len(req['request']['nlu']['tokens']) != 1:  #проверяю сколько слов ввел пользователь
                find_name = ' '.join(req['request']['nlu']['tokens'][1::])
                cursor.execute("SELECT full_note, note_date FROM users WHERE user_id = %s AND note_name = %s", (user_id, find_name))
                records = cursor.fetchall()
                if len(records) == 1:
                    response_text = records[0][0]  
                elif len(records) == 0:
                    response_text = 'Нет записи с таким названием'
                else:
                    date_list = [str(i[1]) for i in records]
                    response_text = f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберете интересующий Вас день"
                    cursor.execute("UPDATE user_states SET state = %s, description = %s WHERE user_id = %s AND funk = %s", (True, find_name, user_id, funk_4))
            else:
                response_text = 'Вы не указали имя заметки'
        else:
            cursor.execute("SELECT funk, state FROM user_states WHERE user_id = %s", (user_id,))  #вытаскиваю из бд значение поля state
            for row in cursor.fetchall():
                if row == ('create_name', True):  #проверяю нужно ли создавать имя записи
                    cursor.execute("INSERT INTO users (note_date, note_name, user_id) VALUES (%s, %s, %s)", (date_today, user_text, user_id))
                    response_text = 'Имя заметки сохранено. Начало записи...'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_2))
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (True, user_id, funk_1))
                    break
                elif row == ('create_note', True):  #проверяю нужно ли создавать запись
                    cursor.execute("SELECT note_name FROM users WHERE user_id = %s AND note_date = %s", (user_id, date_today))
                    records = cursor.fetchall()
                    for i in records[-1]:
                        name = i
                    cursor.execute("UPDATE users SET full_note = %s WHERE note_name = %s AND note_date = %s", (user_text, name, date_today))
                    response_text = 'Новая запись успешно добавлена!'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_1))
                    break
                elif row == ('delete_note', True):  #проверяю нужно ли удалять запись
                    cursor.execute("SELECT note_date FROM users WHERE note_name = %s AND user_id = %s", (user_text, user_id))
                    records = cursor.fetchall()
                    if len(records) == 1:  #если запись всего одна
                        cursor.execute("DELETE FROM users WHERE note_name = %s AND user_id = %s", (user_text, user_id))
                        response_text = 'Запись успешно удалена!'
                    elif len(records) > 1:  #если несколько записей с одинаковым названием
                        cursor.execute("UPDATE user_states SET state = %s, description = %s WHERE user_id = %s AND funk = %s", (True, user_text, user_id, funk_5))
                        date_list = [str(i[0]) for i in records]
                        response_text = f"Запись с таким названием была сделана в следующие дни: {', '.join(date_list)}. Выберете интересующий Вас день"
                    else:
                        response_text = 'У вас нет записи с таким названием'
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_3))
                    break
                elif row == ('find_note', True):  #ищет запись с определенным названием
                    cursor.execute("SELECT description FROM user_states WHERE user_id = %s AND funk = %s", (user_id, funk_4))
                    name = cursor.fetchall()[0][0]
                    note_date = user_text
                    cursor.execute("SELECT full_note FROM users WHERE note_name = %s AND note_date = %s", (name, note_date))
                    response_text = cursor.fetchall()[0][0]
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_4))
                    break
                elif row == ('delete_note_by_date', True):  #удаляет запись по дате, если записей несколько
                    cursor.execute("SELECT description FROM user_states WHERE user_id = %s AND funk = %s", (user_id, funk_5))
                    name = cursor.fetchall()[0][0]
                    note_date = user_text
                    cursor.execute("DELETE FROM users WHERE user_id = %s AND note_date = %s AND note_name = %s", (user_id, note_date, name))
                    cursor.execute("UPDATE user_states SET state = %s WHERE user_id = %s AND funk = %s", (False, user_id, funk_5))
                    response_text = 'Запись успешно удалена!'
                    break
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