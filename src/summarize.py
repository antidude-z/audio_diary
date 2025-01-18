"""Everything related to creation of short note forms,
including side-tasks like scheduler setup for regular IAM-token updates."""

import datetime
import os
from typing import Dict

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from note_storage import NoteStorage


async def make_post_request(url: str, data: Dict, headers: Dict | None = None) -> Dict | None:
    """Make a simple asynchronous POST-request and return JSON in case of success."""

    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, json=data, headers=headers) as res:
            if res.status == 200:
                return await res.json()


async def create_short_note(text: str, user_id: str, title: str, date: datetime.date) -> None:
    """A delayed background task which makes a request to YandexGPT and receives shortened text form as a response,
    adding it to the database."""

    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
    headers = {"Content-Type": "application/json; charset=utf-8",
               "Authorization": f"Bearer {os.getenv('IAM_TOKEN')}"}
    data = {
        "modelUri": f"gpt://{os.getenv('CATALOG_ID')}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.9,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": "Сократи и лаконично перефразируй текст. Объём текста должен быть сокращён минимум вдвое. "
                        "Ты должен передать основную суть, события и, самое главное, эмоции."
            },
            {
                "role": "user",
                "text": text
            }
        ]
    }

    json: Dict = await make_post_request(url, data, headers)
    result: str = json['result']['alternatives'][0]['message']['text']
    async with NoteStorage(user_id) as db:
        await db.add_short_note_form(title, date, result)


async def obtain_new_iam_token() -> None:
    """Ask Yandex for a new IAM-token and assign it to an environment variable."""

    url = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    data = {
        "yandexPassportOauthToken": os.getenv('OAUTH_TOKEN')
    }
    json: Dict = await make_post_request(url, data)
    os.environ['IAM_TOKEN'] = json['iamToken']


async def start_scheduler(app: aiohttp.web.Application) -> None:
    """On application start, obtain new IAM token as well as create new scheduler for doing this every hour."""

    await obtain_new_iam_token()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(obtain_new_iam_token, "interval", hours=1)
    scheduler.start()
    app['scheduler'] = scheduler


async def cleanup_scheduler(app: aiohttp.web.Application) -> None:
    """Shut the scheduler down."""

    app['scheduler'].shutdown()
