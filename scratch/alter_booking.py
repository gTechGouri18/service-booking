import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="service_booking"
)
cur = conn.cursor()

alter_sqls = [
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS advance_percentage INT DEFAULT 20",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS advance_amount DECIMAL(10,2) DEFAULT 0.00",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS remaining_amount DECIMAL(10,2) DEFAULT 0.00",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_status ENUM('pending', 'advance_paid', 'fully_paid', 'refunded', 'non_refundable') DEFAULT 'pending'",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS cancelled_by ENUM('none', 'customer', 'professional') DEFAULT 'none'",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS refund_status VARCHAR(150) DEFAULT 'none'",
    "ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'UPI / Online'"
]

for sql in alter_sqls:
    try:
        cur.execute(sql)
        print("Success:", sql[:45])
    except Exception as e:
        print("Note:", e)

conn.commit()
cur.execute("DESCRIBE booking")
for row in cur.fetchall():
    print(row[0], row[1], row[4])

cur.close()
conn.close()
