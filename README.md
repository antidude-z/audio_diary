# Аудио дневник для Алисы
здесь будет его описание + необходимые инструкции для развертывания на сервере

# сборка:

docker compose -f docker/docker-compose.yml --env-file env/.env build --no-cache

docker compose -f docker/docker-compose.yml --env-file env/.env push

# загрузка и развертка:

cd /srv/audio_diary

docker compose pull

docker compose up -d

docker compose down
