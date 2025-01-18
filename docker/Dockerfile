FROM python:3.10

WORKDIR /usr/src/audio_diary
COPY /src .
COPY requirements.txt .
COPY certificate.pem .
COPY csr.pem .
COPY private_key.pem .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "./app.py"]