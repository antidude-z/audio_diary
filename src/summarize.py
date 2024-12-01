import os
import aiohttp
from note_storage import NoteStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# TODO: comments + refactor
async def obtain_new_iam_token():
    async with aiohttp.ClientSession() as session:
        url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
        data = {
            "yandexPassportOauthToken": os.getenv('OAUTH_TOKEN')
        }
        async with session.post(url=url, json=data) as res:
            if res.status == 200:
                json = await res.json()
                os.environ['IAM_TOKEN'] = json['iamToken']

async def start_scheduler(app):
    await obtain_new_iam_token()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(obtain_new_iam_token, "interval", hours=1)
    scheduler.start()
    app['scheduler'] = scheduler

async def cleanup_scheduler(app):
    app['scheduler'].shutdown()

async def create_short_note(text, user_id, title, date):
    async with aiohttp.ClientSession() as session:
        url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
        headers = {"Content-Type": "application/json; charset=utf-8",
                   "Authorization": f"Bearer {os.getenv('IAM_TOKEN')}"}
        data = {
            "modelUri": f"gpt://{os.getenv('CATALOG_ID')}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": "2000"
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Сократи текст, сохранив его смысл. Не используй никакое форматирование. "
                            "Выдай только лаконичный перефразированный текст. "
                            "Не предлагай сайты с информацией на эту тему"
                },
                {
                    "role": "user",
                    "text": text
                }
            ]
        }

        async with session.post(url=url, json=data, headers=headers) as res:
            if res.status == 200:
                json = await res.json()
                result = json['result']['alternatives'][0]['message']['text']
                async with NoteStorage(user_id) as db:
                    await db.execute('update_short_note', (result, title, date))
