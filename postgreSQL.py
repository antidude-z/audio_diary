import psycopg2
from psycopg2 import Error


try:
    conn = psycopg2.connect(dbname='my_users', user='postgres', 
                            password='2G5i7r1a6f3E', host='localhost')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    conn.commit()  #нужно для сохранения изменений, если таковые были
    records = cursor.fetchall()
    print(records)
    #for row in cursor:
        #print(row)

except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)

finally:  #закрываем соедеинение и курсор
    if conn:
        cursor.close()
        conn.close()
        print("Соединение с PostgreSQL закрыто")