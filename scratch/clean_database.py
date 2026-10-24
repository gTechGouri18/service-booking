import mysql.connector

def wipe_and_reset():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="service_booking"
    )
    cursor = conn.cursor()

    tables = [
        "job_applications",
        "job_posts",
        "reviews",
        "booking",
        "works",
        "services",
        "shops",
        "users"
    ]

    print("==============================================")
    print("STARTING FULL DATABASE RESET (TABLES -> ID 1)")
    print("==============================================")

    # Disable foreign key checks for clean truncate
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

    for table in tables:
        cursor.execute(f"TRUNCATE TABLE `{table}`;")
        cursor.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1;")
        print(f" [CLEARED] Table '{table}' truncated and AUTO_INCREMENT reset to 1.")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()

    # Verify counts and next auto_increment
    print("\nVerification of Table Status:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
        count = cursor.fetchone()[0]
        cursor.execute(f"""
            SELECT AUTO_INCREMENT 
            FROM information_schema.tables 
            WHERE table_schema = 'service_booking' AND table_name = '{table}';
        """)
        ai_res = cursor.fetchone()
        next_id = ai_res[0] if ai_res else "N/A"
        print(f" -> {table:<20} Rows: {count:<5} Next AUTO_INCREMENT ID: {next_id}")

    cursor.close()
    conn.close()
    print("==============================================")
    print("ALL TABLES HAVE BEEN COMPLETELY RESET TO ID 1!")
    print("==============================================")

if __name__ == "__main__":
    wipe_and_reset()
