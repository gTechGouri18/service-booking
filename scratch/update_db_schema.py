import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="service_booking"
)
cursor = conn.cursor()
cursor.execute("ALTER TABLE users MODIFY COLUMN User_type ENUM('customer','professional','admin') NOT NULL;")
conn.commit()

cursor.execute("DESCRIBE users;")
for col in cursor.fetchall():
    if col[0] == 'User_type':
        print("Updated column successfully:", col)

cursor.close()
conn.close()
