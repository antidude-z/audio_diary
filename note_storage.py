import psycopg2
import datetime

class NoteStorage:
    @classmethod
    def setup(cls, user, password, host):
        cls.dbname = 'my_users'  # subject to change in the future
        cls.user = user
        cls.password = password
        cls.host = host

    def __init__(self, user_id):
        self.conn = psycopg2.connect(dbname=self.dbname, user=self.user,
                        password=self.password, host=self.host)
        self.cursor = self.conn.cursor()
        self.user_id = user_id

    def add_note(self, name, note_text):
        query = "INSERT INTO user_notes (user_id, note_name, note_date, full_note) VALUES (%s, %s, %s, %s)"
        self.cursor.execute(query, (self.user_id, name, datetime.date.today(), note_text))

    def select_all_notes_by_name(self, name):
        query = "SELECT full_note, note_date FROM user_notes WHERE user_id = %s AND note_name = %s"
        self.cursor.execute(query, (self.user_id, name))

        return self.cursor.fetchall()

    def select_note(self, name, date):
        query = "SELECT full_note FROM user_notes WHERE note_name = %s AND note_date = %s"
        self.cursor.execute(query, (name, date))

        return self.cursor.fetchall()[0][0]

    def delete_note_by_name_only(self, name):
        query = "DELETE FROM user_notes WHERE note_name = %s AND user_id = %s"
        self.cursor.execute(query, (name, self.user_id))

    def delete_note(self, name, date):
        query = "DELETE FROM user_notes WHERE user_id = %s AND note_date = %s AND note_name = %s"
        self.cursor.execute(query, (self.user_id, date, name))

    def close(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
