import psycopg2
import datetime
import json

#TODO: ПРОПИСАТЬ ДОКУМЕНТАЦИЮ?. Посмотреть гайд по докам.
#TODO: type hints доделать. (как проверять аргументы на тип? или это делается автоматически?)

class NoteStorage:
    QUERIES = json.load(open('sql_queries.json'))

    @classmethod
    def setup(cls, user: str, password: str, host: str) -> None:
        cls.dbname = 'my_users'  # subject to change in the future
        cls.user = user
        cls.password = password
        cls.host = host

    def __init__(self, user_id: str) -> None:
        self.conn = psycopg2.connect(dbname=self.dbname, user=self.user,
                        password=self.password, host=self.host)
        self.cursor = self.conn.cursor()
        self.user_id = user_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def execute(self, query_id: str, *args, fetch: bool=False):
        query = self.QUERIES[query_id]
        self.cursor.execute(query, (self.user_id, *args))

        if fetch:
            return self.cursor.fetchall()

    def add_note(self, name: str, note_text: str) -> None:
        self.execute("add_note", name, datetime.date.today(), note_text)

    def select_all_notes(self):
        return self.execute("select_all_notes", fetch=True)

    def select_all_notes_by_name(self, name: str) -> list:
        return self.execute("select_all_notes_by_name", name, fetch=True)

    def select_note(self, name: str, date_str: str) -> str:
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

        return self.execute('select_note', name, date, fetch=True)[0][0]

    def delete_note(self, name: str, date_str: str=None) -> None:
        if date_str is not None:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            self.execute('delete_note_1', name, date)
        else:
            self.execute('delete_note_2', name)

    def close_connection(self) -> None:
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
