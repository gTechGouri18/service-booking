import os
import sys
import unittest
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, get_db, init_db, save_and_optimize_image

class FullPlatformVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

        # Clean tables before testing
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for t in ['users', 'shops', 'services', 'works', 'booking', 'job_applications', 'job_posts', 'reviews']:
            cur.execute(f"TRUNCATE TABLE {t};")
            cur.execute(f"ALTER TABLE {t} AUTO_INCREMENT = 1;")
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        cur.close()
        conn.close()

    def test_01_image_optimization_and_storage(self):
        """Test Pillow image compression saves disk space and handles collision-free names"""
        # Create a mock high-resolution image in memory (2400x1800)
        img_buffer = BytesIO()
        test_img = Image.new("RGB", (2400, 1800), color=(180, 160, 150))
        test_img.save(img_buffer, format="JPEG", quality=95)
        raw_size = len(img_buffer.getvalue())
        img_buffer.seek(0)
        img_buffer.filename = "high_res_hairstyle_photo.jpg"

        upload_dir = app.config["UPLOAD_FOLDER"]
        saved_filename = save_and_optimize_image(img_buffer, prefix="test_opt", max_dimension=1600, quality=85)
        
        saved_path = os.path.join(upload_dir, saved_filename)
        self.assertTrue(os.path.exists(saved_path), "Optimized image was not saved on disk.")

        # Check saved image dimensions & size
        with Image.open(saved_path) as saved_img:
            w, h = saved_img.size
            self.assertLessEqual(max(w, h), 1600, "Image was not resized to max_dimension.")

        compressed_size = os.path.getsize(saved_path)
        self.assertLess(compressed_size, raw_size, "Compressed image should be significantly smaller than raw image.")
        print(f" [PASS] Storage Optimization: Raw {raw_size} bytes -> Optimized {compressed_size} bytes (Saved {round((1 - compressed_size/raw_size)*100, 1)}% storage!)")

    def test_02_customer_signup_and_id_1(self):
        """Verify Customer Signup starts cleanly with User ID 1"""
        res = self.client.post("/signup", data={
            "name": "Priya Sharma",
            "email": "priya@gmail.com",
            "phone": "9876543210",
            "password": "pass123",
            "user_type": "customer"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE Email = 'priya@gmail.com'")
        user = cur.fetchone()
        conn.close()

        self.assertIsNotNone(user)
        self.assertEqual(user["Id"], 1, "First customer must have ID = 1")
        self.assertEqual(user["User_type"], "customer")
        print(" [PASS] Customer Signup: Generated User ID = 1 successfully.")

    def test_03_professional_signup_and_shop_id_1(self):
        """Verify Professional Signup starts cleanly with User ID 2 and Shop ID 1"""
        dummy_img = BytesIO()
        Image.new("RGB", (800, 600), color="pink").save(dummy_img, format="JPEG")
        dummy_img.seek(0)

        res = self.client.post("/signup", data={
            "name": "Aman Verma",
            "email": "aman@gmail.com",
            "phone": "9826012345",
            "password": "pass123",
            "user_type": "professional",
            "shop_name": "Aman Hairstyle & Salon",
            "work_image": (dummy_img, "salon_sample.jpg")
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE Email = 'aman@gmail.com'")
        user = cur.fetchone()
        cur.execute("SELECT * FROM shops WHERE User_id = %s", (user["Id"],))
        shop = cur.fetchone()
        conn.close()

        self.assertEqual(user["Id"], 2)
        self.assertEqual(user["User_type"], "professional")
        self.assertIsNotNone(shop)
        self.assertEqual(shop["Id"], 1, "First shop must have Shop ID = 1")
        print(" [PASS] Professional Signup: Generated User ID = 2 and Shop ID = 1.")

    def test_04_admin_registration(self):
        """Verify Admin Registration with admin123 key"""
        res = self.client.post("/admin/register", data={
            "name": "Super Admin",
            "email": "admin@servicehub.com",
            "phone": "9000000000",
            "password": "adminpass123",
            "secret_key": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE Email = 'admin@servicehub.com'")
        admin_user = cur.fetchone()
        conn.close()

        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_user["Id"], 3)
        self.assertEqual(admin_user["User_type"], "admin")
        print(" [PASS] Admin Registration: Generated Admin User ID = 3.")

    def test_05_shop_profile_configuration(self):
        """Verify updating shop profile with service charge, local/regional travel charges"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user_type"] = "professional"
            sess["user_name"] = "Aman Verma"

        qr_dummy = BytesIO()
        Image.new("RGB", (300, 300), color="white").save(qr_dummy, format="JPEG")
        qr_dummy.seek(0)

        res = self.client.post("/shop_profile", data={
            "shop_name": "Aman Luxury Hair Studio",
            "owner_name": "Aman Verma",
            "phone": "9826012345",
            "address": "Shop 4, Civic Center, Sector 6",
            "city": "Bhilai",
            "state": "Chhattisgarh",
            "service_area": "Bhilai, Durg, Raipur and surrounding districts",
            "work_details": "Master Stylist specializing in bridal couture hairstyles, party looks, and grooming.",
            "service_charge": "400",
            "local_travel_charge": "60",
            "other_city_charge": "250",
            "other_state_charge": "700",
            "upi_id": "aman@upi",
            "qr_code": (qr_dummy, "aman_qr.jpg")
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM shops WHERE User_id = 2")
        shop = cur.fetchone()
        conn.close()

        self.assertEqual(shop["Shop_name"], "Aman Luxury Hair Studio")
        self.assertEqual(shop["City"], "Bhilai")
        self.assertEqual(shop["Service_charge"], "400")
        self.assertEqual(float(shop["Local_travel_charge"]), 60.0)
        self.assertEqual(float(shop["Other_city_charge"]), 250.0)
        self.assertEqual(float(shop["Other_state_charge"]), 700.0)
        self.assertTrue(shop["qr_code"].startswith("qr_u2_"), "QR code should be uniquely named.")
        print(" [PASS] Shop Profile: Updated with Service Charge Rs. 400 & Travel Charges.")

    def test_06_add_hairstyle_service_and_works_photo(self):
        """Verify service offering under Hairstyle category & work photo with charge '500 / 1000'"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user_type"] = "professional"
            sess["user_name"] = "Aman Verma"

        # Add Service
        res_serv = self.client.post("/my_services", data={
            "service_name": "Bridal Couture Hairstyle",
            "category": "Hairstyle",
            "price": "1200",
            "description": "Premium traditional and modern bridal hairstyle styling with accessories."
        }, follow_redirects=True)
        self.assertEqual(res_serv.status_code, 200)

        # Upload Work Photo with service charge '500 / 1000'
        photo_dummy = BytesIO()
        Image.new("RGB", (1200, 900), color=(150, 100, 120)).save(photo_dummy, format="JPEG")
        photo_dummy.seek(0)

        res_work = self.client.post("/my_works", data={
            "title": "Royal Bridal Hairstyle & Curls",
            "service_charge": "500 / 1000",
            "description": "Intricate bridal curls styling with pearl pins and hair jewelry.",
            "image": (photo_dummy, "bridal_curls.jpg")
        }, follow_redirects=True)
        self.assertEqual(res_work.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM services WHERE user_id = 2")
        s = cur.fetchone()
        cur.execute("SELECT * FROM works WHERE User_id = 2 ORDER BY id DESC")
        w = cur.fetchone()
        conn.close()

        self.assertEqual(s["service_name"], "Bridal Couture Hairstyle")
        self.assertEqual(s["category"], "Hairstyle")
        self.assertEqual(w["service_charge"], "500 / 1000")
        print(" [PASS] Hairstyle Service & Work Photo: Uploaded with Charge '500 / 1000'.")

    def test_07_public_profile_video_removal_and_coverage_map(self):
        """Verify /professional/2 has NO video player and HAS coverage map and 500 / 1000 charge"""
        res = self.client.get("/professional/2")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertNotIn("videoCinemaModal", html, "Intro video modal must not exist.")
        self.assertNotIn("<video", html, "HTML5 video element must not exist.")
        self.assertNotIn("threeDCardWrapper", html, "3D card wrapper must not exist.")
        self.assertIn("500 / 1000", html, "Hairstyle service charge must be visible.")
        self.assertIn("studioCoverageMap", html, "Studio Coverage Map container must exist.")
        self.assertIn("Live Coverage Radius & Distance Map", html)
        print(" [PASS] Professional Profile: 0 Video references, Hairstyle Charge '500 / 1000' and Coverage Map verified.")

    def test_08_booking_with_distance_mapping(self):
        """Verify customer booking creation starting at Booking ID 1 with travel charge and advance"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_type"] = "customer"
            sess["user_name"] = "Priya Sharma"

        # Customer books Home Service with mapped distance 12.5 KM (Local Zone <= 15 KM -> ₹60)
        res = self.client.post("/book/2", data={
            "service": "Bridal Couture Hairstyle",
            "estimated_price": "1200",
            "service_type": "home",
            "booking_date": "2026-10-25",
            "booking_time": "14:00",
            "mapped_distance_km": "12.5",
            "doorstep_address": "Sector 9, Bhilai",
            "city": "Bhilai",
            "state": "Chhattisgarh",
            "advance_percentage": "20",
            "payment_method": "PhonePe UPI"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM booking WHERE Id = 1")
        b = cur.fetchone()
        conn.close()

        self.assertIsNotNone(b, "First booking must exist with ID = 1.")
        self.assertEqual(b["Id"], 1)
        self.assertEqual(b["Customer_id"], 1)
        self.assertEqual(b["Professional_id"], 2)
        self.assertEqual(float(b["Travel_charge"]), 60.0) # Local rate applied
        self.assertEqual(float(b["Charge"]), 1260.0)      # 1200 + 60
        self.assertEqual(float(b["advance_amount"]), 252.0) # 20% of 1260
        self.assertEqual(float(b["remaining_amount"]), 1008.0)
        self.assertIn("Sector 9", b["Location"])
        print(" [PASS] Booking Flow: Generated Booking ID = 1 with accurate Distance Travel Fee Rs. 60 & 20% Advance Rs. 252.")

    def test_09_dashboards_and_jobs_marketplace(self):
        """Verify Customer Dashboard, Professional Dashboard, and Job Postings"""
        # Customer dashboard
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_type"] = "customer"
        res_cust = self.client.get("/customer_dashboard")
        self.assertEqual(res_cust.status_code, 200)
        self.assertIn("Bridal Couture Hairstyle", res_cust.get_data(as_text=True))

        # Professional dashboard
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["user_type"] = "professional"
        res_pro = self.client.get("/professional_dashboard")
        self.assertEqual(res_pro.status_code, 200)

        # Post a Job Offer
        res_job = self.client.post("/jobs/post", data={
            "post_type": "need_worker",
            "title": "Need Senior Bridal Hairstyle Artist",
            "category": "Hairstyle",
            "description": "Looking for expert bridal hairstylist for upcoming wedding season.",
            "skills_required": "Bridal hair, braiding, crimping, accessories",
            "salary": "₹25,000 / month",
            "commission_percentage": "15%",
            "working_hours": "10:00 AM - 7:00 PM",
            "location": "Civic Center",
            "city": "Bhilai",
            "contact_name": "Aman Verma",
            "contact_phone": "9826012345"
        }, follow_redirects=True)
        self.assertEqual(res_job.status_code, 200)

        res_jobs_list = self.client.get("/jobs")
        self.assertEqual(res_jobs_list.status_code, 200)
        self.assertIn("Need Senior Bridal Hairstyle Artist", res_jobs_list.get_data(as_text=True))
        print(" [PASS] Dashboards & Jobs Marketplace: Verified successfully.")

    def test_10_admin_command_center(self):
        """Verify Admin Command Center access"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 3
            sess["user_type"] = "admin"
            sess["is_admin"] = True

        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Priya Sharma", html)
        self.assertIn("Aman Verma", html)
        print(" [PASS] Admin Command Center: Displaying registered users and platform stats.")

if __name__ == "__main__":
    unittest.main()
