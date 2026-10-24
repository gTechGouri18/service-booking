import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='service_booking')
c = conn.cursor(dictionary=True)

for table in ['users', 'shops', 'works', 'services']:
    c.execute(f"DESCRIBE {table}")
    cols = [r['Field'] for r in c.fetchall()]
    print(f"{table}: {cols}")

c.execute("SELECT * FROM shops LIMIT 2")
print("Sample shops:", c.fetchall())

c.execute("SELECT * FROM works LIMIT 5")
print("Sample works:", c.fetchall())

conn.close()
