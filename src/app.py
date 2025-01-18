"""A main module which handles Alice requests at core level and contains all dialog status handlers with most of the
skill functionality."""

import ssl
from typing import Dict

from aiohttp import web
from aiohttp.web_response import Response as AioResponse

from dialog_manager import (DialogStatus, DialogRequest, DialogResponse, status_handler,
                            get_handler, StatusHandlerType)
from handlers import new_note, del_note, find_note, list_notes  # Initialise all the handlers
from summarize import start_scheduler, cleanup_scheduler


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
        res.send_message('Добро пожаловать в «Аудиодневник»! Я могу создать новую голосовую заметку или '
                         'рассказать о ранее записанном событии, по желанию сократив его. '
                         'Команды "удалить заметку" и "мои записи" тоже поддерживаются. Обращайтесь!')
    elif req.exit_current_status:
        res.send_message('Команда отменена.')
    else:
        res.send_message('Извините, не понял Вас. Попробуйте переформулировать запрос или попросите меня помочь.')


# Below are many self-explanatory handlers that go through various dialog scenarios step-by-step.

@status_handler(DialogStatus.HELP_ME)
async def help_me(req: DialogRequest, res: DialogResponse) -> None:
    text = ('Чтобы создать запись, скажите: "новая заметка".\n'
            'Чтобы удалить существующую заметку, скажите "Удалить" и имя вашей заметки, '
            'а если Вы хотите послушать свою запись, сообщите мне её название, после чего '
            ' я предложу Вам выбрать краткую или полную форму рассказа.\n'
            'По команде "мои заметки" я напомню вам, что вы записывали ранее.')

    res.send_message(text)


@status_handler(DialogStatus.WHAT_CAN_YOU_DO)
async def what_can_you_do(req: DialogRequest, res: DialogResponse) -> None:
    text = ('Я умею запоминать ваши слова, создавая заметки, и преобразовывать их в краткую форму. '
            'После добавления новой записи у вас будет два варианта обращения к ней: просмотр полной '
            'или краткой формы записи. ')

    res.send_message(text)


ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain(certfile='certificate.pem', keyfile='private_key.pem')
ssl_context.set_ciphers('ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256')
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

app: web.Application = web.Application()
app.add_routes([web.post('/', main)])
app.on_startup.append(start_scheduler)
app.on_cleanup.append(cleanup_scheduler)
web.run_app(app, port=5000, ssl_context=ssl_context)
