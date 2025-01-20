# Аудио дневник для Алисы
Инструмент для быстрой и удобной записи мыслей в аудио-формате; поддерживает добавление, удаление, просмотр заметок.
Файл будет дополнен в будущем :)

# сборка:

docker compose -f docker/docker-compose.yml --env-file env/.env build --no-cache

docker compose -f docker/docker-compose.yml --env-file env/.env push

# загрузка и развертка:

cd /srv/audio_diary

docker compose pull

docker compose up -d

docker compose down