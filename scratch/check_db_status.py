import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='service_booking')
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM users;")
print("Users count:", c.fetchone()[0])

c.execute("SELECT table_name, AUTO_INCREMENT, table_rows FROM information_schema.tables WHERE table_schema='service_booking';")
for row in c.fetchall():
    print(row)

# Reset users auto increment to 1 if empty
c.execute("SELECT COUNT(*) FROM users;")
cnt = c.fetchone()[0]
if cnt == 0:
    c.execute("ALTER TABLE users AUTO_INCREMENT = 1;")
    conn.commit()
    print("Users table reset to AUTO_INCREMENT = 1")

c.close()
conn.close()
