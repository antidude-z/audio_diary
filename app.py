from flask import Flask, request
import json


app = Flask(__name__)


@app.route('/', methods=['POST'])
def main():
    req = request.json
    intent_id = req['request']['nlu']['intents']

    with open('C:/Users/user/.vscode/python/alice/my.json', 'r') as file:  #открываю файл
        data = json.load(file)  #беру json

    my_json = json.loads(data)  #json -> dict

    if req['session']['new']:  #проверяю сессию: новая -> True, нет -> False
        response_text = 'Начало работы тестового навыка'
    else:
        if intent_id.get('new_note') != None:  #обрабатываю запрос пользователя
            response_text = 'Начало записи'
            my_json['new_note'] = True  #переписываю json, чтобы при следующем запросе знать, что делать
        elif intent_id.get('del_note') != None:  #обрабатываю другой вариант запроса пользователя
            response_text = 'Запись успешно удалена'
        else:
            if my_json['new_note']:  #проверяю нужно ли выполнять функцию new_note
                '''место для добавления заметки в БД'''
                response_text = 'Новая запись успешно добавлена'
                my_json['new_note'] = False  #после выполнения переписываю значение в json,
                #чтобы обозначить добавление новой записи
            else:
                response_text = 'запрос не распознан'

    my_json = json.dumps(my_json)  #dict -> json

    with open('C:/Users/user/.vscode/python/alice/my.json', 'w') as file:  #передаю новый json
        json.dump(my_json, file)

    response = {
        'version': req['version'],
        'session': req['session'],
        'response': {
            'text': response_text,
            'end_session': False
        },
    }
    return response


app.run('0.0.0.0', port=5000, debug=True)