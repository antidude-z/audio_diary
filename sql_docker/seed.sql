CREATE DATABASE diary
    WITH
    OWNER = "admin"
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.utf8'
    LC_CTYPE = 'en_US.utf8'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;

\c diary

CREATE TABLE IF NOT EXISTS public.user_notes
(
    title character varying COLLATE pg_catalog."default",
    user_id character varying COLLATE pg_catalog."default",
    date date,
    full_note character varying COLLATE pg_catalog."default",
    short_note character varying COLLATE pg_catalog."default"
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public.user_notes
    OWNER to "admin";