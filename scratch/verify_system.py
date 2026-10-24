import mysql.connector

conn = mysql.connector.connect(host='localhost', user='root', password='', database='service_booking')
cur = conn.cursor(dictionary=True)
cur.execute('DESCRIBE booking')
cols = cur.fetchall()
print('=== BOOKING COLUMNS ===')
for c in cols:
    print(f" - {c['Field']}: {c['Type']}")

cur.execute('SELECT COUNT(*) as cnt FROM users')
print('Users count:', cur.fetchone()['cnt'])

cur.execute('SELECT COUNT(*) as cnt FROM shops')
print('Shops count:', cur.fetchone()['cnt'])

cur.execute('SELECT COUNT(*) as cnt FROM booking')
print('Booking count:', cur.fetchone()['cnt'])

cur.execute('SELECT COUNT(*) as cnt FROM job_posts')
print('Job posts count:', cur.fetchone()['cnt'])

conn.close()
