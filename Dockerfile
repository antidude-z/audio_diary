FROM python:3.10

WORKDIR /usr/src/audio_diary
COPY /src .
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "./app.py"]