import mysql.connector, shutil, os

uploads_dir = os.path.abspath("static/uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Copy sample work images to uploads
shutil.copy("static/images/parlour_work.jpg", os.path.join(uploads_dir, "styleshair_bridal_styling.jpg"))
shutil.copy("static/images/spa_facial_luxury.jpg", os.path.join(uploads_dir, "styleshair_spa_glow.jpg"))

conn = mysql.connector.connect(host='localhost', user='root', password='', database='service_booking')
cursor = conn.cursor(dictionary=True)

# Check works
cursor.execute("SELECT COUNT(*) as cnt FROM works WHERE user_id = 1")
cnt = cursor.fetchone()["cnt"]

if cnt == 0:
    cursor.execute("""
        INSERT INTO works (user_id, title, description, image)
        VALUES 
        (1, 'Bridal & Reception Hair Artistry (ब्राइडल हेयर स्टाइलिंग)', 'Specialist bridal buns, curls, designer accessories setting and long-lasting hair styling for weddings and grand parties.', 'styleshair_bridal_styling.jpg'),
        (1, 'Hair Spa & Keratin Therapy (हेयर स्पा और केराटिन केयर)', 'Deep conditioning, damage repair, scalp revitalization and premium smoothing treatment with imported organic hair masks.', 'styleshair_spa_glow.jpg')
    """)
    print("Inserted 2 works for User 1")

# Check services
cursor.execute("SELECT COUNT(*) as cnt FROM services WHERE user_id = 1")
s_cnt = cursor.fetchone()["cnt"]

if s_cnt == 0:
    cursor.execute("""
        INSERT INTO services (user_id, service_name, category, price, description)
        VALUES 
        (1, 'Bridal & Party Hair Styling', 'Hair & Styling', 800.00, 'Designer bridal curls, buns and festive hairstyles with hair accessories setup.'),
        (1, 'Hair Spa & Deep Keratin Treatment', 'Hair & Spa', 1200.00, 'Intensive nourishing hair therapy for smooth, frizz-free, radiant hair.'),
        (1, 'Precision Cut & Blow Dry', 'Hair Care', 350.00, 'Modern layer / step cut with professional salon wash and blow dry styling.')
    """)
    print("Inserted 3 services for User 1")

conn.commit()
cursor.close()
conn.close()
print("Seed complete successfully!")
