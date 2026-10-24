import mysql.connector

def update_schema():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="service_booking"
    )
    cur = conn.cursor()
    queries = [
        "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS salary VARCHAR(100) DEFAULT ''",
        "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS commission_percentage VARCHAR(50) DEFAULT ''",
        "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS working_hours VARCHAR(100) DEFAULT ''"
    ]
    for q in queries:
        try:
            cur.execute(q)
            print(" [OK]", q)
        except Exception as e:
            print(" [NOTE]", e)
    conn.commit()

    print("\nCurrent job_posts schema:")
    cur.execute("DESCRIBE job_posts")
    for r in cur.fetchall():
        print(f" - {r[0]:<25} {r[1]:<20} Null:{r[2]} Key:{r[3]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    update_schema()
