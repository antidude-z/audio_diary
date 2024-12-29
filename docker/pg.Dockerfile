FROM postgres:16
EXPOSE 5432
COPY docker/seed.sql /docker-entrypoint-initdb.d/

