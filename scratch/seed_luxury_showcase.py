import mysql.connector, shutil, os

uploads_dir = os.path.abspath("static/uploads")
os.makedirs(uploads_dir, exist_ok=True)

# Copy category images to uploads if not present
for src_name, dst_name in [
    ("parlour_work.jpg", "parlour_work.jpg"),
    ("spa_facial_luxury.jpg", "spa_facial_luxury.jpg"),
    ("electrician_work.jpg", "electrician_work.jpg"),
    ("ac_repair_work.jpg", "ac_repair_work.jpg"),
    ("plumber_work.jpg", "plumber_work.jpg"),
    ("home_cleaning_luxury.jpg", "home_cleaning_luxury.jpg"),
]:
    src = os.path.join("static/images", src_name)
    dst = os.path.join(uploads_dir, dst_name)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)

conn = mysql.connector.connect(host='localhost', user='root', password='', database='service_booking')
cursor = conn.cursor(dictionary=True)

# 1. Seed Professionals
pros = [
    {
        "name": "Rajesh Sharma",
        "email": "rajesh.electric@servicehub.com",
        "phone": "9826112233",
        "shop_name": "VoltCraft Precision Electricals",
        "city": "Bhilai",
        "state": "Chhattisgarh",
        "area": "Bhilai & Durg",
        "work_details": "Certified electrical engineer with 6+ years experience. Expert in residential wiring, smart lighting installation, MCB panel repair, and appliance troubleshooting. Available 9am to 8pm.",
        "local_charge": 50.0,
        "other_city": 250.0,
        "other_state": 600.0,
        "work_img": "electrician_work.jpg",
        "work_title": "Smart Architectural Lighting & Circuit Tuning",
        "work_desc": "Installed designer LED ambient cove lighting, modern chandelier fixtures, and balanced MCB electrical distribution panel.",
        "services": [
            ("Complete House Wiring Inspection", "Electrical", 650.0, "Full diagnostic check of all circuits, switchboards, earthing and load balancing."),
            ("Chandelier & Luxury Fixtures Install", "Lighting", 450.0, "Precision ceiling anchor mounting and safe electrical connection for chandeliers."),
            ("MCB & Short Circuit Repair", "Repair", 300.0, "Rapid diagnosis of tripped breakers, power surges, and wire burnout replacement.")
        ]
    },
    {
        "name": "Amit Patel",
        "email": "amit.coolzone@servicehub.com",
        "phone": "9827334455",
        "shop_name": "CoolZone HVAC & Climate Systems",
        "city": "Raipur",
        "state": "Chhattisgarh",
        "area": "Raipur & Naya Raipur",
        "work_details": "Specialized HVAC technician with 8 years of experience. We provide high-pressure jet cleaning for split and inverter AC units, genuine refrigerant charging, and compressor repairs with a 30-day service warranty.",
        "local_charge": 100.0,
        "other_city": 350.0,
        "other_state": 800.0,
        "work_img": "ac_repair_work.jpg",
        "work_title": "Deep Jet Cleansing & Refrigerant Recharging",
        "work_desc": "High-pressure hydrodynamic jet wash of cooling coils, indoor blower wheel sanitization, and R32 eco-friendly gas top-up.",
        "services": [
            ("Deep Foam & Jet AC Cleansing", "AC Service", 599.0, "Complete indoor and outdoor pressure wash with anti-fungal foam treatment."),
            ("Refrigerant Gas Refill (R32 / R410A)", "Gas Refill", 1499.0, "Leakage detection, nitrogen pressure testing, and precision weight gas refill."),
            ("Split AC Installation / Uninstallation", "Installation", 899.0, "Bracket mounting, copper pipe insulation wrapping, and vacuumized gas release.")
        ]
    },
    {
        "name": "Vikram Singh",
        "email": "vikram.aquapro@servicehub.com",
        "phone": "9828556677",
        "shop_name": "AquaPro Sanitary & Plumbing Studio",
        "city": "Durg",
        "state": "Chhattisgarh",
        "area": "Durg, Bhilai & Rajnandgaon",
        "work_details": "Master plumber with 5+ years experience. Modern bathroom fitting, concealed leak detection, booster pump installations, and premium chrome sanitary ware fitting.",
        "local_charge": 80.0,
        "other_city": 300.0,
        "other_state": 750.0,
        "work_img": "plumber_work.jpg",
        "work_title": "Luxury Marble Vanity & Concealed Mixer Fitting",
        "work_desc": "Precision installation of concealed wall-hung commode, thermostatic shower mixer, and polished gold basin faucets.",
        "services": [
            ("Rapid Leak Repair & Pipe Concealment", "Plumbing", 350.0, "Acoustic detection and repair of underground / concealed wall water leakages."),
            ("Bathroom Fixtures & Diverter Setup", "Sanitary", 550.0, "Installation of modern rain showers, faucets, and concealed diverter valves."),
            ("Water Motor & Pressure Pump Install", "Pump Service", 650.0, "Setup of automatic pressure booster pumps with check-valve synchronization.")
        ]
    }
]

for p in pros:
    # Check if user exists
    cursor.execute("SELECT Id FROM users WHERE Email = %s", (p["email"],))
    u = cursor.fetchone()
    if not u:
        cursor.execute("""
            INSERT INTO users (Name, Email, Phone, Password, User_type)
            VALUES (%s, %s, %s, 'pass123', 'professional')
        """, (p["name"], p["email"], p["phone"]))
        uid = cursor.lastrowid
    else:
        uid = u["Id"]

    # Check shop
    cursor.execute("SELECT Id FROM shops WHERE User_id = %s", (uid,))
    s = cursor.fetchone()
    if not s:
        cursor.execute("""
            INSERT INTO shops (User_id, Shop_name, Owner_name, Phone, Address, City, State, Service_area, Work_details, Local_travel_charge, Other_city_charge, Other_state_charge)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            uid, p["shop_name"], p["name"], p["phone"],
            f"Studio Hub, Main Road, {p['city']}", p["city"], p["state"], p["area"],
            p["work_details"], p["local_charge"], p["other_city"], p["other_state"]
        ))
        shop_id = cursor.lastrowid
    else:
        shop_id = s["Id"]

    # Check works
    cursor.execute("SELECT Id FROM works WHERE user_id = %s", (uid,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO works (user_id, title, description, image)
            VALUES (%s, %s, %s, %s)
        """, (uid, p["work_title"], p["work_desc"], p["work_img"]))

    # Check services
    cursor.execute("SELECT id FROM services WHERE user_id = %s", (uid,))
    if not cursor.fetchone():
        for sname, cat, price, desc in p["services"]:
            cursor.execute("""
                INSERT INTO services (user_id, service_name, category, price, description)
                VALUES (%s, %s, %s, %s, %s)
            """, (uid, sname, cat, price, desc))

# 2. Seed Sample Job Posts
cursor.execute("SELECT COUNT(*) as cnt FROM job_posts")
j_cnt = cursor.fetchone()["cnt"]
if j_cnt == 0:
    jobs = [
        (2, "Complete Bridal Hair Styling & Makeup Required (ब्राइडल हेयर स्टाइलिंग और मेकअप)", "Hair & Beauty", "₹3,500", "Sector 9, Bhilai", "Bhilai", "G Gouri", "9202745205", "Wedding reception on 25th Oct. Need a certified hair stylist with designer accessories setup at our residence."),
        (2, "3 BHK Complete Electrical Rewiring & Chandelier Mounting (घर की पूरी वायरिंग)", "Electrical", "₹2,800", "Shankar Nagar, Raipur", "Raipur", "G Gouri", "9202745205", "Renovating our 3 BHK flat. Need new MCB board, concealed wire pulling, and 4 luxury chandelier fixtures mounting."),
        (2, "Split AC Cooling Leak Repair & Jet Cleansing (एसी कूलिंग रिपेयर और जेट क्लीनिंग)", "AC Service", "₹1,200", "Civil Lines, Raipur", "Raipur", "G Gouri", "9202745205", "Split AC is not cooling properly and blowing warm air. Need gas pressure testing and jet filter wash.")
    ]
    for uid, title, cat, budget, loc, city, cname, cphone, desc in jobs:
        cursor.execute("""
            INSERT INTO job_posts (user_id, post_type, title, category, budget, location, city, contact_name, contact_phone, description, status)
            VALUES (%s, 'need_worker', %s, %s, %s, %s, %s, %s, %s, %s, 'open')
        """, (uid, title, cat, budget, loc, city, cname, cphone, desc))

# 3. Seed Reviews for pro 1 if none
cursor.execute("SELECT COUNT(*) as cnt FROM reviews WHERE Professional_id = 1")
if cursor.fetchone()["cnt"] == 0:
    cursor.execute("""
        INSERT INTO reviews (Customer_id, Professional_id, Booking_id, Rating, Review)
        VALUES 
        (2, 1, 1, 5, 'Gouri did an extraordinary bridal hairstyle for my sister. Long lasting curls, very gentle and punctual! Highly recommended.'),
        (2, 1, 1, 5, 'The hair spa treatment was so relaxing. My hair feels incredibly soft and frizz-free. 10/10 service!')
    """)

conn.commit()
cursor.close()
conn.close()
print("Seeding showcase professionals, works, services, jobs, and reviews complete!")
