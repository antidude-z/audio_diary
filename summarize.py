import aiohttp
from note_storage import NoteStorage

url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
headers = {"Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer t1.9euelZrOip7ImpfKns-Xk5mJkJ2bku3rnpWayZmWzsiZmMfGzo2MjZuZnZ3l8_c6XWlF-e9AGBUX_t3z93oLZ0X570AYFRf-zef1656VmpOej8yLl8-QmZmax5PMxpTM7_zF656VmpOej8yLl8-QmZmax5PMxpTM.m7Nt61_SN32AyMbmceD8SiII3YmOL1vOn4iHMaNzVdrLc5H5Pg8oEiqPUJqsYewAHg5uraIdUdcugQlUuEQkDw"}

async def summarize(text, user_id, title, date):
  async with aiohttp.ClientSession() as session:
    data = {
      "modelUri": "gpt://b1g1dmlkotd6au2fhg2k/yandexgpt-lite",
      "completionOptions": {
        "stream": False,
        "temperature": 0.6,
        "maxTokens": "2000"
      },
      "messages": [
        {
          "role": "system",
          "text": "Кратко и лаконично перепиши текст, сохранив его смысл"
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
          await db.execute('add_short_note', (result, title, date))
