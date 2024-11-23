import psycopg2
import json
from typing import Union

class NoteStorage:
    QUERIES: dict[str, str] = json.load(open('sql_queries.json'))

    @classmethod
    def setup(cls, db_user: str, password: str, host: str) -> None:
        cls.db_name = 'my_users'  # Subject to change in the future
        cls.db_user = db_user
        cls.password = password
        cls.host = host

    def __init__(self, user_id: str) -> None:
        # Connecting to 'PostgreSQL' database where all user notes are stored
        self.conn = psycopg2.connect(dbname=self.db_name, user=self.db_user,
                        password=self.password, host=self.host)
        self.cursor = self.conn.cursor()
        self.user_id = user_id

    # These dunder methods are implemented for a custom context manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_connection()

    def execute(self, query_id: str, args: Union[tuple, str]=None) -> Union[list, None]:
        # To make sure only current user's notes are affected, each query must have user_id as its first var
        query = self.QUERIES[query_id]

        # Depending on args value, we need to pass these arguments into cursor method differently
        if isinstance(args, tuple):
            self.cursor.execute(query, (self.user_id, *args))
        elif isinstance(args, str):
            self.cursor.execute(query, (self.user_id, args))
        else:
            self.cursor.execute(query, (self.user_id,))

        # If we are expecting any output from given query, return it, otherwise return None
        try:
            return self.cursor.fetchall()
        except psycopg2.ProgrammingError:
            return None

    def close_connection(self) -> None:
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
