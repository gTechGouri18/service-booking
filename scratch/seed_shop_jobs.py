import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="service_booking"
)
cursor = conn.cursor(dictionary=True)

# Delete older customer dummy jobs so only shop owner jobs remain
cursor.execute("DELETE FROM job_posts WHERE user_id NOT IN (SELECT User_id FROM shops)")
conn.commit()

# Check if shop jobs already exist
cursor.execute("SELECT COUNT(*) as cnt FROM job_posts WHERE user_id IN (SELECT User_id FROM shops)")
cnt = cursor.fetchone()["cnt"]

if cnt == 0:
    cursor.execute("""
        INSERT INTO job_posts 
        (user_id, post_type, title, category, description, skills_required, budget, location, city, contact_name, contact_phone, status)
        VALUES 
        (
            1, 
            'need_worker', 
            'Senior Bridal Hair Stylist & Makeup Specialist', 
            'Salon & Beauty', 
            'Styleshair Studio is expanding our bridal team. Looking for an experienced hair stylist skilled in couture styling, bridal updos, blowdrys, and skin glow rituals.', 
            'Bridal hair styling, blowdry, facial rituals, salon etiquette', 
            '18000/month', 
            'Sector-7 Studio, Main Market', 
            'Bhilai', 
            'G Gouri', 
            '9202745205', 
            'open'
        ),
        (
            8, 
            'need_worker', 
            'Certified Assistant Electrician & Wiring Technician', 
            'Electrical', 
            'VoltCraft Precision Electricals is hiring a dedicated assistant electrician for residential wiring, panel troubleshooting, inverter setups, and lighting fixtures.', 
            'Domestic wiring, inverter setup, multimeter testing, safety protocols', 
            '15000/month', 
            'Nehru Nagar East', 
            'Bhilai', 
            'Rajesh Sharma', 
            '9876543210', 
            'open'
        )
    """)
    conn.commit()
    print("Inserted 2 shop owner job offers.")
else:
    print(f"Shop owner job offers already exist: {cnt}")

cursor.close()
conn.close()
