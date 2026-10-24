from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
import uuid
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.secret_key = "service_booking_secret_key_12345"

# Enhanced Storage & Publishing Configuration (Up to 32MB uploads, smart compression)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB max upload limit
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.errorhandler(413)
def request_entity_too_large(error):
    flash("Uploaded file is too large. Maximum allowed size is 32MB.")
    return redirect(request.url)


def save_and_optimize_image(file_storage, prefix="img", max_dimension=1600, quality=85):
    """
    Saves an uploaded image with a collision-free filename and optimizes/compresses
    it using Pillow to conserve server storage capacity (saving up to 85-90% disk space)
    for high scalability when published.
    """
    if not file_storage or not file_storage.filename:
        return ""

    upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(app.static_folder, "uploads"))
    os.makedirs(upload_dir, exist_ok=True)

    orig_name = secure_filename(file_storage.filename)
    if not orig_name:
        orig_name = "upload.jpg"
    name_base, ext = os.path.splitext(orig_name)
    ext = ext.lower() if ext else ".jpg"

    unique_filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{orig_name}"
    target_path = os.path.join(upload_dir, unique_filename)

    try:
        file_storage.seek(0)
        img = Image.open(file_storage)

        # Handle RGBA conversion for JPEG
        if ext in [".jpg", ".jpeg"]:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

        # Downscale oversized mobile images while preserving sharp aspect ratio
        w, h = img.size
        if max(w, h) > max_dimension:
            scale = max_dimension / float(max(w, h))
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save with web-optimized compression
        if ext in [".jpg", ".jpeg"]:
            img.save(target_path, "JPEG", optimize=True, quality=quality)
        elif ext == ".png":
            img.save(target_path, "PNG", optimize=True)
        elif ext == ".webp":
            img.save(target_path, "WEBP", quality=quality)
        else:
            file_storage.seek(0)
            file_storage.save(target_path)
    except Exception:
        file_storage.seek(0)
        file_storage.save(target_path)

    return unique_filename


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="service_booking"
    )


def init_db():
    """Ensure all required tables, columns, BIGINT primary/foreign keys, and high-speed indexes exist in database for multi-million row scale"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Users table (BIGINT supports 9+ Quintillion customer & artisan accounts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                Id BIGINT AUTO_INCREMENT PRIMARY KEY,
                Name VARCHAR(255) NOT NULL,
                Email VARCHAR(255) NOT NULL UNIQUE,
                Phone VARCHAR(50) NOT NULL,
                Password VARCHAR(255) NOT NULL,
                User_type ENUM('customer','professional','admin') NOT NULL,
                Client_no BIGINT DEFAULT NULL,
                Pro_no BIGINT DEFAULT NULL,
                Admin_no BIGINT DEFAULT NULL,
                Created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Alter users columns if previously created with smaller INT or VARCHAR
        alter_users = [
            "ALTER TABLE users MODIFY COLUMN Id BIGINT AUTO_INCREMENT",
            "ALTER TABLE users MODIFY COLUMN User_type ENUM('customer','professional','admin') NOT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS Client_no BIGINT DEFAULT NULL",
            "ALTER TABLE users MODIFY COLUMN Client_no BIGINT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS Pro_no BIGINT DEFAULT NULL",
            "ALTER TABLE users MODIFY COLUMN Pro_no BIGINT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS Admin_no BIGINT DEFAULT NULL",
            "ALTER TABLE users MODIFY COLUMN Admin_no BIGINT DEFAULT NULL",
            "ALTER TABLE users MODIFY COLUMN Name VARCHAR(255) NOT NULL",
            "ALTER TABLE users MODIFY COLUMN Email VARCHAR(255) NOT NULL",
            "ALTER TABLE users MODIFY COLUMN Phone VARCHAR(50) NOT NULL",
            "ALTER TABLE users ROW_FORMAT=DYNAMIC"
        ]
        for au in alter_users:
            try:
                cursor.execute(au)
            except Exception:
                pass

        # Shops table (BIGINT User_id, expansive TEXT & MEDIUMTEXT)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shops (
                Id BIGINT AUTO_INCREMENT PRIMARY KEY,
                User_id BIGINT NOT NULL,
                Shop_name VARCHAR(255) NOT NULL,
                Owner_name VARCHAR(255) NOT NULL,
                Phone VARCHAR(50) NOT NULL,
                Address TEXT NOT NULL,
                City VARCHAR(150) NOT NULL,
                State VARCHAR(150) NOT NULL,
                Service_area TEXT NOT NULL,
                Work_details MEDIUMTEXT NOT NULL,
                Other_city_charge DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                Other_state_charge DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                Local_travel_charge DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                upi_id VARCHAR(150) DEFAULT '',
                qr_code VARCHAR(255) DEFAULT '',
                Service_charge VARCHAR(255) DEFAULT '0'
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Works / Portfolio table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS works (
                Id BIGINT AUTO_INCREMENT PRIMARY KEY,
                User_id BIGINT NOT NULL,
                title VARCHAR(255) NOT NULL,
                description MEDIUMTEXT NOT NULL,
                image VARCHAR(255) NOT NULL,
                service_charge VARCHAR(255) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Booking table (BIGINT IDs, high-precision amounts, TEXT location)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS booking (
                Id BIGINT AUTO_INCREMENT PRIMARY KEY,
                Customer_id BIGINT NOT NULL,
                Professional_id BIGINT NOT NULL,
                Shop_id BIGINT NOT NULL,
                Service VARCHAR(255) NOT NULL,
                Service_Type VARCHAR(100) NOT NULL,
                Booking_date DATE NOT NULL,
                Booking_time TIME NOT NULL,
                Location TEXT NOT NULL,
                Charge DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                Status ENUM('pending','accepted','completed','cancelled') NOT NULL DEFAULT 'pending',
                Travel_charge DECIMAL(12,2) DEFAULT 0.00,
                advance_percentage INT DEFAULT 20,
                advance_amount DECIMAL(12,2) DEFAULT 0.00,
                remaining_amount DECIMAL(12,2) DEFAULT 0.00,
                payment_status ENUM('pending','advance_paid','fully_paid','refunded','non_refundable') DEFAULT 'pending',
                cancelled_by ENUM('none','customer','professional') DEFAULT 'none',
                refund_status VARCHAR(255) DEFAULT 'none',
                payment_method VARCHAR(100) DEFAULT 'UPI / Online'
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                Id BIGINT AUTO_INCREMENT PRIMARY KEY,
                Booking_id BIGINT NOT NULL,
                Customer_id BIGINT NOT NULL,
                Professional_id BIGINT NOT NULL,
                Rating INT NOT NULL,
                Review MEDIUMTEXT,
                Created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Services table (Offered by professionals)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                service_name VARCHAR(255) NOT NULL,
                category VARCHAR(150) NULL,
                price DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                description MEDIUMTEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Job Posts table (Job Need portal)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_posts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                post_type ENUM('need_worker', 'need_job') DEFAULT 'need_worker',
                title VARCHAR(255) NOT NULL,
                category VARCHAR(150) NOT NULL,
                description LONGTEXT NOT NULL,
                skills_required TEXT NULL,
                budget VARCHAR(150) NULL,
                location TEXT NOT NULL,
                city VARCHAR(150) NOT NULL,
                contact_name VARCHAR(150) NOT NULL,
                contact_phone VARCHAR(50) NOT NULL,
                status ENUM('open', 'closed') DEFAULT 'open',
                salary VARCHAR(150) DEFAULT '',
                commission_percentage VARCHAR(100) DEFAULT '',
                working_hours VARCHAR(150) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Job Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_applications (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                job_id BIGINT NOT NULL,
                applicant_id BIGINT NOT NULL,
                applicant_name VARCHAR(150) NOT NULL,
                applicant_phone VARCHAR(50) NOT NULL,
                experience_years VARCHAR(100) NULL,
                message MEDIUMTEXT NULL,
                status ENUM('applied', 'shortlisted', 'rejected') DEFAULT 'applied',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB ROW_FORMAT=DYNAMIC DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)

        # Add / modify columns across tables for ultra high-scale persistence
        alter_queries = [
            "ALTER TABLE shops MODIFY COLUMN Id BIGINT AUTO_INCREMENT",
            "ALTER TABLE shops MODIFY COLUMN User_id BIGINT NOT NULL",
            "ALTER TABLE shops MODIFY COLUMN Address TEXT NOT NULL",
            "ALTER TABLE shops MODIFY COLUMN Service_area TEXT NOT NULL",
            "ALTER TABLE shops MODIFY COLUMN Work_details MEDIUMTEXT NOT NULL",
            "ALTER TABLE shops ADD COLUMN IF NOT EXISTS Local_travel_charge DECIMAL(12,2) NOT NULL DEFAULT 0.00",
            "ALTER TABLE shops ADD COLUMN IF NOT EXISTS upi_id VARCHAR(150) DEFAULT ''",
            "ALTER TABLE shops ADD COLUMN IF NOT EXISTS qr_code VARCHAR(255) DEFAULT ''",
            "ALTER TABLE shops ADD COLUMN IF NOT EXISTS Service_charge VARCHAR(255) DEFAULT '0'",
            "ALTER TABLE shops ROW_FORMAT=DYNAMIC",
            "ALTER TABLE works MODIFY COLUMN Id BIGINT AUTO_INCREMENT",
            "ALTER TABLE works MODIFY COLUMN User_id BIGINT NOT NULL",
            "ALTER TABLE works MODIFY COLUMN description MEDIUMTEXT NOT NULL",
            "ALTER TABLE works ADD COLUMN IF NOT EXISTS service_charge VARCHAR(255) DEFAULT ''",
            "ALTER TABLE works ROW_FORMAT=DYNAMIC",
            "ALTER TABLE booking MODIFY COLUMN Id BIGINT AUTO_INCREMENT",
            "ALTER TABLE booking MODIFY COLUMN Customer_id BIGINT NOT NULL",
            "ALTER TABLE booking MODIFY COLUMN Professional_id BIGINT NOT NULL",
            "ALTER TABLE booking MODIFY COLUMN Shop_id BIGINT NOT NULL",
            "ALTER TABLE booking MODIFY COLUMN Location TEXT NOT NULL",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS advance_percentage INT DEFAULT 20",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS advance_amount DECIMAL(12,2) DEFAULT 0.00",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS remaining_amount DECIMAL(12,2) DEFAULT 0.00",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_status ENUM('pending','advance_paid','fully_paid','refunded','non_refundable') DEFAULT 'pending'",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS cancelled_by ENUM('none','customer','professional') DEFAULT 'none'",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS refund_status VARCHAR(255) DEFAULT 'none'",
            "ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_method VARCHAR(100) DEFAULT 'UPI / Online'",
            "ALTER TABLE booking ROW_FORMAT=DYNAMIC",
            "ALTER TABLE services MODIFY COLUMN id BIGINT AUTO_INCREMENT",
            "ALTER TABLE services MODIFY COLUMN user_id BIGINT NOT NULL",
            "ALTER TABLE services MODIFY COLUMN description MEDIUMTEXT NULL",
            "ALTER TABLE services ROW_FORMAT=DYNAMIC",
            "ALTER TABLE reviews MODIFY COLUMN Id BIGINT AUTO_INCREMENT",
            "ALTER TABLE reviews MODIFY COLUMN Booking_id BIGINT NOT NULL",
            "ALTER TABLE reviews MODIFY COLUMN Customer_id BIGINT NOT NULL",
            "ALTER TABLE reviews MODIFY COLUMN Professional_id BIGINT NOT NULL",
            "ALTER TABLE reviews MODIFY COLUMN Review MEDIUMTEXT",
            "ALTER TABLE reviews ROW_FORMAT=DYNAMIC",
            "ALTER TABLE job_posts MODIFY COLUMN id BIGINT AUTO_INCREMENT",
            "ALTER TABLE job_posts MODIFY COLUMN user_id BIGINT NOT NULL",
            "ALTER TABLE job_posts MODIFY COLUMN description LONGTEXT NOT NULL",
            "ALTER TABLE job_posts MODIFY COLUMN location TEXT NOT NULL",
            "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS salary VARCHAR(150) DEFAULT ''",
            "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS commission_percentage VARCHAR(100) DEFAULT ''",
            "ALTER TABLE job_posts ADD COLUMN IF NOT EXISTS working_hours VARCHAR(150) DEFAULT ''",
            "ALTER TABLE job_posts ROW_FORMAT=DYNAMIC",
            "ALTER TABLE job_applications MODIFY COLUMN id BIGINT AUTO_INCREMENT",
            "ALTER TABLE job_applications MODIFY COLUMN job_id BIGINT NOT NULL",
            "ALTER TABLE job_applications MODIFY COLUMN applicant_id BIGINT NOT NULL",
            "ALTER TABLE job_applications MODIFY COLUMN message MEDIUMTEXT NULL",
            "ALTER TABLE job_applications ROW_FORMAT=DYNAMIC"
        ]
        for aq in alter_queries:
            try:
                cursor.execute(aq)
            except Exception:
                pass

        # High-Speed B-Tree Indexes for fast lookups across millions of rows
        index_queries = [
            ("users", "idx_users_type", "User_type"),
            ("users", "idx_users_client_no", "Client_no"),
            ("users", "idx_users_pro_no", "Pro_no"),
            ("users", "idx_users_admin_no", "Admin_no"),
            ("shops", "idx_shops_user", "User_id"),
            ("shops", "idx_shops_city", "City"),
            ("works", "idx_works_user", "User_id"),
            ("booking", "idx_booking_customer", "Customer_id"),
            ("booking", "idx_booking_pro", "Professional_id"),
            ("booking", "idx_booking_shop", "Shop_id"),
            ("booking", "idx_booking_status", "Status"),
            ("booking", "idx_booking_date", "Booking_date"),
            ("reviews", "idx_reviews_pro", "Professional_id"),
            ("reviews", "idx_reviews_cust", "Customer_id"),
            ("services", "idx_services_user", "user_id"),
            ("services", "idx_services_category", "category"),
            ("job_posts", "idx_job_posts_user", "user_id"),
            ("job_posts", "idx_job_posts_status", "status"),
            ("job_applications", "idx_job_apps_job", "job_id"),
            ("job_applications", "idx_job_apps_applicant", "applicant_id")
        ]
        for tbl, idx_name, col in index_queries:
            try:
                cursor.execute(f"CREATE INDEX {idx_name} ON {tbl}({col})")
            except Exception:
                pass

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Database init note:", e)


# Run DB initialization
init_db()


# -------------------------------------------------------------
# Home & Authentication Routes
# -------------------------------------------------------------

@app.route("/")
def home():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1. Get featured shops with ratings
    cursor.execute("""
        SELECT s.*, 
               COALESCE(ROUND(AVG(r.Rating), 1), 5.0) as avg_rating, 
               COUNT(r.Id) as review_count
        FROM shops s
        LEFT JOIN reviews r ON s.User_id = r.Professional_id
        GROUP BY s.Id
        ORDER BY s.Id DESC
        LIMIT 6
    """)
    featured_shops = cursor.fetchall()

    for shop in featured_shops:
        cursor.execute("SELECT service_name, price FROM services WHERE user_id = %s LIMIT 3", (shop["User_id"],))
        shop["services"] = cursor.fetchall()
        cursor.execute("SELECT image FROM works WHERE user_id = %s ORDER BY id DESC LIMIT 1", (shop["User_id"],))
        work_img = cursor.fetchone()
        shop["cover_image"] = work_img["image"] if work_img else None

    # 2. Get trending services offered across platform
    cursor.execute("""
        SELECT s.*, sh.Shop_name, sh.City, sh.User_id as professional_id
        FROM services s
        LEFT JOIN shops sh ON s.user_id = sh.User_id
        ORDER BY s.id DESC
        LIMIT 6
    """)
    trending_services = cursor.fetchall()

    for s in trending_services:
        cursor.execute("SELECT image FROM works WHERE user_id = %s ORDER BY id DESC LIMIT 1", (s["professional_id"],))
        w = cursor.fetchone()
        if w and w["image"]:
            s["image"] = f"/static/uploads/{w['image']}"
        else:
            cat = (s.get("category") or s.get("service_name") or "").lower()
            if "hair" in cat or "beauty" in cat or "salon" in cat:
                s["image"] = "/static/images/parlour_work.jpg"
            elif "spa" in cat or "facial" in cat:
                s["image"] = "/static/images/spa_facial_luxury.jpg"
            elif "electric" in cat or "wire" in cat:
                s["image"] = "/static/images/electrician_work.jpg"
            elif "ac" in cat or "cool" in cat or "hvac" in cat:
                s["image"] = "/static/images/ac_repair_work.jpg"
            elif "plumb" in cat or "sanitary" in cat:
                s["image"] = "/static/images/plumber_work.jpg"
            else:
                s["image"] = "/static/images/hero_luxury.jpg"

    # 3. Get professional portfolio works
    cursor.execute("""
        SELECT w.*, sh.Shop_name, sh.City
        FROM works w
        LEFT JOIN shops sh ON w.user_id = sh.User_id
        ORDER BY w.id DESC
        LIMIT 6
    """)
    portfolio_works = cursor.fetchall()

    # 4. Get customer testimonials
    cursor.execute("""
        SELECT r.*, u.Name as Customer_name, sh.Shop_name
        FROM reviews r
        JOIN users u ON r.Customer_id = u.Id
        LEFT JOIN shops sh ON r.Professional_id = sh.User_id
        ORDER BY r.Id DESC
        LIMIT 4
    """)
    customer_reviews = cursor.fetchall()

    # 5. Get verified shop owner job offers (Marketplace)
    cursor.execute("""
        SELECT jp.*, s.Shop_name, s.Owner_name, s.City as shop_city
        FROM job_posts jp
        JOIN shops s ON jp.user_id = s.User_id
        JOIN users u ON jp.user_id = u.Id AND u.User_type = 'professional'
        WHERE jp.status = 'open'
        ORDER BY jp.id DESC
        LIMIT 4
    """)
    recent_jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "home.html",
        shops=featured_shops,
        services=trending_services,
        works=portfolio_works,
        reviews=customer_reviews,
        jobs=recent_jobs
    )


@app.route("/conditions")
def conditions():
    return render_template("conditions.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form["phone"].strip()
        password = request.form["password"]
        user_type = request.form["user_type"]

        if user_type == "admin":
            secret_key = request.form.get("admin_secret_key", "").strip()
            if secret_key not in ["admin123", "admin", "servicehub@2026", "servicehub_admin"]:
                flash("Invalid Administrator Security Key! Registration as Admin requires verified passcode (e.g. admin123).")
                return render_template("signup.html")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        try:
            client_no = None
            pro_no = None
            admin_no = None

            if user_type == "customer":
                cursor.execute("SELECT COALESCE(MAX(Client_no), 0) + 1 AS next_no FROM users WHERE User_type = 'customer'")
                row = cursor.fetchone()
                client_no = row["next_no"] if row else 1
                cursor.execute("""
                    INSERT INTO users
                    (Name, Email, Phone, Password, User_type, Client_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, email, phone, password, user_type, client_no))
            elif user_type == "professional":
                cursor.execute("SELECT COALESCE(MAX(Pro_no), 0) + 1 AS next_no FROM users WHERE User_type = 'professional'")
                row = cursor.fetchone()
                pro_no = row["next_no"] if row else 1
                cursor.execute("""
                    INSERT INTO users
                    (Name, Email, Phone, Password, User_type, Pro_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, email, phone, password, user_type, pro_no))
            elif user_type == "admin":
                cursor.execute("SELECT COALESCE(MAX(Admin_no), 0) + 1 AS next_no FROM users WHERE User_type = 'admin'")
                row = cursor.fetchone()
                admin_no = row["next_no"] if row else 1
                cursor.execute("""
                    INSERT INTO users
                    (Name, Email, Phone, Password, User_type, Admin_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, email, phone, password, user_type, admin_no))
            else:
                cursor.execute("""
                    INSERT INTO users
                    (Name, Email, Phone, Password, User_type)
                    VALUES (%s, %s, %s, %s, %s)
                """, (name, email, phone, password, user_type))

            new_user_id = cursor.lastrowid

            # If registering as Professional, handle studio setup & work photo upload
            if user_type == "professional":
                shop_name = request.form.get("shop_name", "").strip() or f"{name}'s Studio"
                work_file = request.files.get("work_image")
                work_filename = ""

                if work_file and work_file.filename != "":
                    work_filename = save_and_optimize_image(work_file, prefix=f"work_u{new_user_id}")

                # Initialize shop entry
                cursor.execute("""
                    INSERT INTO shops
                    (User_id, Shop_name, Owner_name, Phone, Address, City, State, Service_area, Work_details, Local_travel_charge)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    new_user_id,
                    shop_name,
                    name,
                    phone,
                    "Studio Address",
                    "Local City",
                    "State",
                    "City Coverage Area",
                    "Professional certified services with quality craftsmanship and on-time arrival.",
                    0.0
                ))

                # Add to portfolio works if work photo provided
                if work_filename:
                    cursor.execute("""
                        INSERT INTO works (user_id, title, description, image)
                        VALUES (%s, %s, %s, %s)
                    """, (new_user_id, f"{name} - Professional Work", "Client work showcase and craftsmanship.", work_filename))

            conn.commit()
            if user_type == "admin":
                flash("Administrator account created successfully! Please log in to Command Center.")
                return redirect(url_for("admin_login"))
            else:
                flash("Account created successfully! Please login to continue.")
                return redirect(url_for("login"))

        except mysql.connector.Error as error:
            flash("Email already registered or database error: " + str(error))

        finally:
            cursor.close()
            conn.close()

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM users
            WHERE Email = %s AND Password = %s
        """, (email, password))

        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user["Id"]
            session["user_type"] = user["User_type"]
            session["user_name"] = user["Name"]
            session["user_email"] = user["Email"]
            session["user_phone"] = user["Phone"]

            flash(f"Welcome back, {user['Name']}!")

            if user["User_type"] == "admin":
                session["is_admin"] = True
                return redirect(url_for("admin"))
            elif user["User_type"] == "customer":
                return redirect(url_for("customer_dashboard"))
            elif user["User_type"] == "professional":
                return redirect(url_for("professional_dashboard"))

        flash("Invalid email or password. Please try again.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if new_password:
            cursor.execute("""
                UPDATE users SET Name = %s, Phone = %s, Password = %s WHERE Id = %s
            """, (name, phone, new_password, user_id))
        else:
            cursor.execute("""
                UPDATE users SET Name = %s, Phone = %s WHERE Id = %s
            """, (name, phone, user_id))

        conn.commit()
        session["user_name"] = name
        session["user_phone"] = phone
        flash("Profile updated successfully!")

    cursor.execute("SELECT * FROM users WHERE Id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("profile.html", user=user)


# -------------------------------------------------------------
# Customer Dashboard & Services
# -------------------------------------------------------------

@app.route("/customer_dashboard")
def customer_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    customer_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch recent bookings
    cursor.execute("""
        SELECT b.*, s.Shop_name, s.Owner_name
        FROM booking b
        JOIN shops s ON b.Shop_id = s.Id
        WHERE b.Customer_id = %s
        ORDER BY b.Id DESC LIMIT 3
    """, (customer_id,))
    recent_bookings = cursor.fetchall()

    # Client No & Counts
    cursor.execute("SELECT Client_no FROM users WHERE Id = %s", (customer_id,))
    u_row = cursor.fetchone()
    client_no = u_row["Client_no"] if (u_row and u_row.get("Client_no")) else 1

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Customer_id = %s", (customer_id,))
    booking_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM job_posts WHERE user_id = %s", (customer_id,))
    job_count = cursor.fetchone()["cnt"]

    cursor.close()
    conn.close()

    return render_template(
        "customer_dashboard.html",
        recent_bookings=recent_bookings,
        booking_count=booking_count,
        job_count=job_count,
        client_no=client_no
    )


# -------------------------------------------------------------
# Professional Dashboard & Management
# -------------------------------------------------------------

@app.route("/professional_dashboard")
def professional_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    professional_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Fetch pro_no
    cursor.execute("SELECT Pro_no FROM users WHERE Id = %s", (professional_id,))
    u_row = cursor.fetchone()
    pro_no = u_row["Pro_no"] if (u_row and u_row.get("Pro_no")) else 1

    # Check if shop profile exists
    cursor.execute("SELECT * FROM shops WHERE User_id = %s", (professional_id,))
    shop = cursor.fetchone()

    # Get stats
    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Professional_id = %s AND Status = 'pending'", (professional_id,))
    pending_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Professional_id = %s AND Status = 'accepted'", (professional_id,))
    accepted_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Professional_id = %s AND Status = 'completed'", (professional_id,))
    completed_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM services WHERE user_id = %s", (professional_id,))
    services_count = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM reviews WHERE Professional_id = %s", (professional_id,))
    reviews_count = cursor.fetchone()["cnt"]

    # Recent booking requests
    cursor.execute("""
        SELECT * FROM booking
        WHERE Professional_id = %s
        ORDER BY Id DESC LIMIT 4
    """, (professional_id,))
    recent_bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "professional_dashboard.html",
        shop=shop,
        pending_count=pending_count,
        accepted_count=accepted_count,
        completed_count=completed_count,
        services_count=services_count,
        reviews_count=reviews_count,
        recent_bookings=recent_bookings,
        pro_no=pro_no
    )


@app.route("/shop_profile", methods=["GET", "POST"])
def shop_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM shops WHERE User_id = %s", (user_id,))
    existing_shop = cursor.fetchone()

    if request.method == "POST":
        shop_name = request.form["shop_name"].strip()
        owner_name = request.form["owner_name"].strip()
        phone = request.form["phone"].strip()
        address = request.form["address"].strip()
        city = request.form["city"].strip()
        state = request.form["state"].strip()
        service_area = request.form["service_area"].strip()
        work_details = request.form["work_details"].strip()
        other_city_charge = float(request.form.get("other_city_charge", 0) or 0)
        other_state_charge = float(request.form.get("other_state_charge", 0) or 0)
        local_travel_charge = float(request.form.get("local_travel_charge", 0) or 0)
        service_charge = request.form.get("service_charge", "0").strip() or "0"
        upi_id = request.form.get("upi_id", "").strip()
        qr_code_file = request.files.get("qr_code")

        qr_filename = existing_shop.get("qr_code", "") if existing_shop else ""

        if qr_code_file and qr_code_file.filename != "":
            qr_filename = save_and_optimize_image(qr_code_file, prefix=f"qr_u{user_id}", max_dimension=1000, quality=95)

        # Handle work portfolio photo upload if selected
        work_file = request.files.get("work_image")
        if work_file and work_file.filename != "":
            work_fn = save_and_optimize_image(work_file, prefix=f"work_u{user_id}")
            work_title = request.form.get("work_title", "").strip() or f"{shop_name} - Featured Work"
            work_charge = request.form.get("work_charge", "").strip() or service_charge
            work_desc = request.form.get("work_desc", "").strip() or "Uploaded artisan craftsmanship portfolio image."
            cursor.execute("""
                INSERT INTO works (user_id, title, description, image, service_charge)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, work_title, work_desc, work_fn, work_charge))

        if existing_shop:
            cursor.execute("""
                UPDATE shops SET
                    Shop_name = %s,
                    Owner_name = %s,
                    Phone = %s,
                    Address = %s,
                    City = %s,
                    State = %s,
                    Service_area = %s,
                    Work_details = %s,
                    Other_city_charge = %s,
                    Other_state_charge = %s,
                    Local_travel_charge = %s,
                    Service_charge = %s,
                    upi_id = %s,
                    qr_code = %s
                WHERE User_id = %s
            """, (
                shop_name, owner_name, phone, address, city, state,
                service_area, work_details, other_city_charge, other_state_charge,
                local_travel_charge, service_charge, upi_id, qr_filename,
                user_id
            ))
            flash("Shop profile updated successfully!")
        else:
            cursor.execute("""
                INSERT INTO shops
                (
                    User_id,
                    Shop_name,
                    Owner_name,
                    Phone,
                    Address,
                    City,
                    State,
                    Service_area,
                    Work_details,
                    Other_city_charge,
                    Other_state_charge,
                    Local_travel_charge,
                    Service_charge,
                    upi_id,
                    qr_code
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_id,
                shop_name,
                owner_name,
                phone,
                address,
                city,
                state,
                service_area,
                work_details,
                other_city_charge,
                other_state_charge,
                local_travel_charge,
                service_charge,
                upi_id,
                qr_filename
            ))
            flash("Shop profile created successfully!")

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for("professional_dashboard"))

    cursor.close()
    conn.close()
    return render_template("shop_profile.html", shop=existing_shop)


@app.route("/my_works", methods=["GET", "POST"])
def my_works():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        service_charge = request.form.get("service_charge", "").strip()
        image = request.files.get("image")

        if image and image.filename != "":
            filename = save_and_optimize_image(image, prefix=f"work_u{user_id}")

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO works
                (user_id, title, description, image, service_charge)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, title, description, filename, service_charge))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Work uploaded successfully!")

        return redirect(url_for("my_works"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM works
        WHERE user_id = %s
        ORDER BY id DESC
    """, (user_id,))
    works = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_works.html", works=works)


@app.route("/delete_work/<int:work_id>")
def delete_work(work_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM works WHERE id = %s AND user_id = %s", (work_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Work item deleted.")
    return redirect(url_for("my_works"))


# -------------------------------------------------------------
# My Services (Professional service listings & prices)
# -------------------------------------------------------------

@app.route("/my_services", methods=["GET", "POST"])
def my_services():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        service_name = request.form["service_name"].strip()
        category = request.form.get("category", "General").strip()
        price = float(request.form.get("price", 0) or 0)
        description = request.form.get("description", "").strip()

        cursor.execute("""
            INSERT INTO services (user_id, service_name, category, price, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, service_name, category, price, description))
        conn.commit()
        flash("Service added successfully!")
        return redirect(url_for("my_services"))

    cursor.execute("SELECT * FROM services WHERE user_id = %s ORDER BY id DESC", (user_id,))
    services = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_services.html", services=services)


@app.route("/delete_service/<int:service_id>")
def delete_service(service_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM services WHERE id = %s AND user_id = %s", (service_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Service deleted successfully.")
    return redirect(url_for("my_services"))


# -------------------------------------------------------------
# Orders & Reviews for Professional
# -------------------------------------------------------------

@app.route("/my_orders")
def my_orders():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    professional_id = session["user_id"]
    status_filter = request.args.get("status", "")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if status_filter:
        cursor.execute("""
            SELECT b.*, u.Name as customer_name, u.Phone as customer_phone
            FROM booking b
            JOIN users u ON b.Customer_id = u.Id
            WHERE b.Professional_id = %s AND b.Status = %s
            ORDER BY b.Id DESC
        """, (professional_id, status_filter))
    else:
        cursor.execute("""
            SELECT b.*, u.Name as customer_name, u.Phone as customer_phone
            FROM booking b
            JOIN users u ON b.Customer_id = u.Id
            WHERE b.Professional_id = %s
            ORDER BY b.Id DESC
        """, (professional_id,))

    orders = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_orders.html", orders=orders, active_status=status_filter)


@app.route("/professional_reviews")
def professional_reviews():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    professional_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT r.*, u.Name as Customer_name, b.Service, b.Booking_date
        FROM reviews r
        JOIN users u ON r.Customer_id = u.Id
        JOIN booking b ON r.Booking_id = b.Id
        WHERE r.Professional_id = %s
        ORDER BY r.Id DESC
    """, (professional_id,))
    reviews = cursor.fetchall()

    # Calculate average rating
    cursor.execute("SELECT AVG(Rating) as avg_rating, COUNT(*) as total_reviews FROM reviews WHERE Professional_id = %s", (professional_id,))
    stat = cursor.fetchone()
    avg_rating = round(stat["avg_rating"], 1) if stat["avg_rating"] else 0
    total_reviews = stat["total_reviews"]

    cursor.close()
    conn.close()

    return render_template(
        "professional_reviews.html",
        reviews=reviews,
        avg_rating=avg_rating,
        total_reviews=total_reviews
    )


# -------------------------------------------------------------
# Public Professional Profile & Work Portfolio Gallery
# -------------------------------------------------------------

@app.route("/professional/<int:professional_id>")
def professional_profile(professional_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1. Shop & Professional details
    cursor.execute("SELECT * FROM shops WHERE User_id = %s", (professional_id,))
    shop = cursor.fetchone()

    # Fallback: check if professional_id was passed as shop.Id
    if not shop:
        cursor.execute("SELECT * FROM shops WHERE Id = %s", (professional_id,))
        shop = cursor.fetchone()
        if shop:
            professional_id = shop["User_id"]

    if not shop:
        cursor.execute("SELECT * FROM users WHERE Id = %s AND User_type = 'professional'", (professional_id,))
        pro_user = cursor.fetchone()
        if pro_user:
            shop = {
                "Id": 0,
                "User_id": pro_user["Id"],
                "Shop_name": f"{pro_user['Name']}'s Studio",
                "Owner_name": pro_user["Name"],
                "Phone": pro_user["Phone"],
                "Address": "Studio Location",
                "City": "Local City",
                "State": "India",
                "Service_area": "City & Doorstep Coverage",
                "Work_details": "Professional verified services with on-time arrival and quality guarantee.",
                "Local_travel_charge": 0.0,
                "Other_city_charge": 0.0,
                "Other_state_charge": 0.0,
                "upi_id": "",
                "qr_code": ""
            }
        else:
            cursor.close()
            conn.close()
            flash("Professional profile not found.")
            return redirect(url_for("find_services"))

    # 2. Portfolio Works / Images
    cursor.execute("""
        SELECT * FROM works 
        WHERE user_id = %s 
        ORDER BY id DESC
    """, (professional_id,))
    works = cursor.fetchall()

    # 3. Services offered
    cursor.execute("""
        SELECT * FROM services 
        WHERE user_id = %s 
        ORDER BY id DESC
    """, (professional_id,))
    services = cursor.fetchall()

    # 4. Verified Client Reviews
    cursor.execute("""
        SELECT r.*, u.Name as customer_name, b.Service, b.Booking_date
        FROM reviews r
        JOIN users u ON r.Customer_id = u.Id
        LEFT JOIN booking b ON r.Booking_id = b.Id
        WHERE r.Professional_id = %s
        ORDER BY r.Id DESC
        LIMIT 6
    """, (professional_id,))
    reviews = cursor.fetchall()

    # 5. Rating stats & Completed orders count
    cursor.execute("""
        SELECT COUNT(*) as total_reviews, 
               COALESCE(ROUND(AVG(Rating), 1), 5.0) as avg_rating 
        FROM reviews 
        WHERE Professional_id = %s
    """, (professional_id,))
    stat = cursor.fetchone()
    avg_rating = stat["avg_rating"] if stat and stat["avg_rating"] else 5.0
    total_reviews = stat["total_reviews"] if stat else 0

    cursor.execute("""
        SELECT COUNT(*) as completed_count 
        FROM booking 
        WHERE Professional_id = %s AND Status = 'completed'
    """, (professional_id,))
    completed_stat = cursor.fetchone()
    completed_count = completed_stat["completed_count"] if completed_stat else 0

    cursor.close()
    conn.close()

    return render_template(
        "professional_profile.html",
        shop=shop,
        works=works,
        services=services,
        reviews=reviews,
        avg_rating=avg_rating,
        total_reviews=total_reviews,
        completed_count=completed_count
    )


# -------------------------------------------------------------
# Customer Find Services & Bookings (with Advance Token Payment)
# -------------------------------------------------------------

@app.route("/find_services")
def find_services():
    search = request.args.get("search", "").strip()
    city = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT s.*, 
               COALESCE(ROUND(AVG(r.Rating), 1), 5.0) as avg_rating, 
               COUNT(r.Id) as review_count
        FROM shops s
        LEFT JOIN reviews r ON s.User_id = r.Professional_id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND (s.Shop_name LIKE %s OR s.Owner_name LIKE %s OR s.Work_details LIKE %s)"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern])

    if city:
        query += " AND s.City LIKE %s"
        params.append(f"%{city}%")

    if location:
        query += " AND (s.Address LIKE %s OR s.Service_area LIKE %s)"
        lpattern = f"%{location}%"
        params.extend([lpattern, lpattern])

    if category:
        query += " AND s.Work_details LIKE %s"
        params.append(f"%{category}%")

    query += " GROUP BY s.Id ORDER BY s.Id DESC"
    cursor.execute(query, tuple(params))
    shops = cursor.fetchall()

    # For each shop, get offerings & portfolio cover image
    for shop in shops:
        cursor.execute("SELECT service_name, price FROM services WHERE user_id = %s LIMIT 3", (shop["User_id"],))
        shop["services"] = cursor.fetchall()
        cursor.execute("SELECT image FROM works WHERE user_id = %s ORDER BY id DESC LIMIT 1", (shop["User_id"],))
        work_img = cursor.fetchone()
        shop["cover_image"] = work_img["image"] if work_img else None

    # Distinct cities
    cursor.execute("SELECT DISTINCT City FROM shops WHERE City != ''")
    cities = [r["City"] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        "find_services.html",
        shops=shops,
        search=search,
        city=city,
        category=category,
        location=location,
        cities=cities
    )


@app.route("/book/<int:professional_id>", methods=["GET", "POST"])
def book_service(professional_id):
    if "user_id" not in session:
        flash("Please login to book a service.")
        return redirect(url_for("login"))

    if session.get("user_type") != "customer":
        if session.get("user_type") == "professional":
            flash("Booking services is exclusively for Customers. As a Professional, you can receive booking requests from customers in your dashboard.")
            return redirect(url_for("professional_dashboard"))
        flash("Only registered customers can book services.")
        return redirect(url_for("home"))

    customer_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Professional shop details
    cursor.execute("SELECT * FROM shops WHERE User_id = %s", (professional_id,))
    shop = cursor.fetchone()

    if not shop:
        cursor.close()
        conn.close()
        flash("Professional shop not found.")
        return redirect(url_for("find_services"))

    # Also fetch services offered by this shop
    cursor.execute("SELECT * FROM services WHERE user_id = %s", (professional_id,))
    services = cursor.fetchall()

    if request.method == "POST":
        service = request.form["service"].strip()
        service_type = request.form["service_type"]
        booking_date = request.form["booking_date"]
        booking_time = request.form["booking_time"]
        payment_method = request.form.get("payment_method", "UPI / Online")

        city = request.form["city"].strip().lower()
        state = request.form["state"].strip().lower()

        shop_city = shop["City"].strip().lower()
        shop_state = shop["State"].strip().lower()

        # Travel charge calculation (configured by professional with mapping knowledge)
        mapped_distance_km = request.form.get("mapped_distance_km")
        if service_type == "parlour":
            travel_charge = 0.0
        elif mapped_distance_km:
            try:
                dist_km = float(mapped_distance_km)
                if dist_km <= 15.0 or city == shop_city:
                    travel_charge = float(shop.get("Local_travel_charge") or 0)
                elif dist_km <= 80.0 or state == shop_state:
                    travel_charge = float(shop.get("Other_city_charge") or 0)
                else:
                    travel_charge = float(shop.get("Other_state_charge") or 0)
            except (ValueError, TypeError):
                if city == shop_city:
                    travel_charge = float(shop.get("Local_travel_charge") or 0)
                elif state == shop_state:
                    travel_charge = float(shop.get("Other_city_charge") or 0)
                else:
                    travel_charge = float(shop.get("Other_state_charge") or 0)
        elif city == shop_city:
            travel_charge = float(shop.get("Local_travel_charge") or 0)
        elif state == shop_state:
            travel_charge = float(shop.get("Other_city_charge") or 0)
        else:
            travel_charge = float(shop.get("Other_state_charge") or 0)

        # Service Estimated Price & Advance Calculation (Default: 20% advance token payment)
        estimated_price = float(request.form.get("estimated_price", 0) or 0)
        if estimated_price <= 0 and services:
            # Check if matching service in shop services
            for s in services:
                if s["service_name"].lower() == service.lower():
                    estimated_price = float(s["price"])
                    break
        if estimated_price <= 0:
            estimated_price = 250.0  # Base standard fallback estimate if not specified

        total_estimated = round(estimated_price + travel_charge, 2)
        advance_percentage = int(request.form.get("advance_percentage", 20))
        advance_amount = round(total_estimated * (advance_percentage / 100), 2)
        remaining_amount = round(total_estimated - advance_amount, 2)

        doorstep_address = request.form.get("doorstep_address", "").strip()
        city_raw = request.form["city"].strip()
        state_raw = request.form["state"].strip()
        if doorstep_address and doorstep_address.lower() != city_raw.lower():
            location = f"{doorstep_address}, {city_raw}, {state_raw}"[:250]
        else:
            location = f"{city_raw}, {state_raw}"[:250]

        cursor.execute("""
            INSERT INTO booking
            (
                Customer_id,
                Professional_id,
                Shop_id,
                Service,
                Service_Type,
                Booking_date,
                Booking_time,
                Location,
                Charge,
                Travel_charge,
                Status,
                advance_percentage,
                advance_amount,
                remaining_amount,
                payment_status,
                cancelled_by,
                refund_status,
                payment_method
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            customer_id,
            professional_id,
            shop["Id"],
            service,
            service_type,
            booking_date,
            booking_time,
            location,
            total_estimated,
            travel_charge,
            "pending",
            advance_percentage,
            advance_amount,
            remaining_amount,
            "advance_paid",
            "none",
            "none",
            payment_method
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Advance token payment of ₹{advance_amount} ({advance_percentage}%) successful! Booking request confirmed. Remaining ₹{remaining_amount} service complete hone ke turant baad pay karna hoga.")
        return redirect(url_for("my_bookings"))

    cursor.close()
    conn.close()

    return render_template("booking.html", shop=shop, services=services)


@app.route("/my_bookings")
def my_bookings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "customer":
        if session.get("user_type") == "professional":
            return redirect(url_for("booking_requests"))
        return redirect(url_for("home"))

    customer_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            booking.Id,
            booking.Customer_id,
            booking.Professional_id,
            booking.Shop_id,
            booking.Service,
            booking.Service_Type,
            booking.Booking_date,
            booking.Booking_time,
            booking.Location,
            booking.Charge,
            booking.Travel_charge,
            booking.Status,
            booking.advance_percentage,
            booking.advance_amount,
            booking.remaining_amount,
            booking.payment_status,
            booking.cancelled_by,
            booking.refund_status,
            booking.payment_method,
            shops.Shop_name,
            shops.Owner_name,
            shops.Phone as Shop_phone
        FROM booking
        JOIN shops ON booking.Shop_id = shops.Id
        WHERE booking.Customer_id = %s
        ORDER BY booking.Id DESC
    """, (customer_id,))

    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("my_bookings.html", bookings=bookings)


@app.route("/pay_remaining/<int:booking_id>", methods=["GET", "POST"])
def pay_remaining(booking_id):
    """Customer pays remaining balance immediately after completion"""
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "customer":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM booking WHERE Id = %s AND Customer_id = %s
    """, (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        flash("Booking not found.")
        return redirect(url_for("my_bookings"))

    rem = float(booking.get("remaining_amount") or 0)

    if request.method == "POST" or request.args.get("confirm") == "1":
        method = request.form.get("payment_method") or booking.get("payment_method") or "UPI / Online"
        cursor.execute("""
            UPDATE booking
            SET payment_status = 'fully_paid',
                remaining_amount = 0.00,
                payment_method = %s
            WHERE Id = %s AND Customer_id = %s
        """, (method, booking_id, session["user_id"]))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Payment of ₹{rem} received successfully! Bill is now fully settled. Please rate your experience.")
        return redirect(url_for("add_review", booking_id=booking_id))

    cursor.close()
    conn.close()
    return redirect(url_for("booking_completed", booking_id=booking_id))


@app.route("/mark_paid/<int:booking_id>")
def mark_paid(booking_id):
    """Professional marks the remaining payment as collected (Cash on spot)"""
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE booking
        SET payment_status = 'fully_paid',
            remaining_amount = 0.00
        WHERE Id = %s AND Professional_id = %s
    """, (booking_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Remaining payment marked as collected successfully!")
    return redirect(url_for("booking_requests"))


@app.route("/customer_cancel_booking/<int:booking_id>")
def customer_cancel_booking(booking_id):
    """
    CUSTOMER CANCELLATION POLICY:
    If customer cancels, the advance payment is NON-REFUNDABLE!
    """
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM booking WHERE Id = %s AND Customer_id = %s", (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        flash("Booking not found.")
        return redirect(url_for("my_bookings"))

    if booking["Status"] in ["completed", "cancelled"]:
        cursor.close()
        conn.close()
        flash("Cannot cancel a completed or already cancelled booking.")
        return redirect(url_for("my_bookings"))

    advance_val = booking.get("advance_amount") or 0

    cursor.execute("""
        UPDATE booking
        SET Status = 'cancelled',
            cancelled_by = 'customer',
            payment_status = 'non_refundable',
            refund_status = 'Non-Refundable (Cancelled by Customer)'
        WHERE Id = %s AND Customer_id = %s
    """, (booking_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"⚠️ Booking #{booking_id} cancelled by you. As per cancellation policy, advance payment of ₹{advance_val} is NON-REFUNDABLE (no return).")
    return redirect(url_for("my_bookings"))


# -------------------------------------------------------------
# Professional Booking Actions (Accept, Set Charge, Cancel with 100% Refund, Complete)
# -------------------------------------------------------------

@app.route("/booking_requests")
def booking_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    professional_id = session["user_id"]
    status_filter = request.args.get("status", "")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if status_filter:
        cursor.execute("""
           SELECT b.*, u.Name as customer_name, u.Phone as customer_phone
           FROM booking b
           JOIN users u ON b.Customer_id = u.Id
           WHERE b.Professional_id = %s AND b.Status = %s
           ORDER BY b.Id DESC
        """, (professional_id, status_filter))
    else:
        cursor.execute("""
           SELECT b.*, u.Name as customer_name, u.Phone as customer_phone
           FROM booking b
           JOIN users u ON b.Customer_id = u.Id
           WHERE b.Professional_id = %s
           ORDER BY b.Id DESC
        """, (professional_id,))

    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("booking_requests.html", bookings=bookings, active_status=status_filter)


@app.route("/accept_booking/<int:booking_id>")
def accept_booking(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE booking
        SET Status = 'accepted'
        WHERE Id = %s AND Professional_id = %s
    """, (booking_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Booking accepted successfully! Work scheduled.")
    return redirect(url_for("booking_requests"))


@app.route("/cancel_booking/<int:booking_id>")
def cancel_booking(booking_id):
    """
    SHOP OWNER CANCELLATION POLICY:
    If professional cancels, the advance payment is 100% REFUNDED to the customer!
    """
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM booking WHERE Id = %s AND Professional_id = %s", (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        flash("Booking not found.")
        return redirect(url_for("booking_requests"))

    advance_val = booking.get("advance_amount") or 0

    cursor.execute("""
        UPDATE booking
        SET Status = 'cancelled',
            cancelled_by = 'professional',
            payment_status = 'refunded',
            refund_status = '100% Refunded (Cancelled by Shop Owner)'
        WHERE Id = %s AND Professional_id = %s
    """, (booking_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Booking #{booking_id} cancelled by shop. As per policy, customer's advance payment of ₹{advance_val} has been 100% REFUNDED to them.")
    return redirect(url_for("booking_requests"))


@app.route("/complete_booking/<int:booking_id>")
def complete_booking(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM booking WHERE Id = %s AND Professional_id = %s", (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        flash("Booking not found.")
        return redirect(url_for("booking_requests"))

    cursor.execute("""
        UPDATE booking
        SET Status = 'completed'
        WHERE Id = %s AND Professional_id = %s AND Status = 'accepted'
    """, (booking_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Booking #{booking_id} marked as Completed! Customer has been prompted to pay the remaining balance of ₹{booking.get('remaining_amount', 0)} immediately.")
    return redirect(url_for("booking_completed", booking_id=booking_id))


@app.route("/booking_completed/<int:booking_id>")
def booking_completed(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.*, s.Shop_name, s.Owner_name, s.Phone as shop_phone, s.upi_id, s.qr_code
        FROM booking b
        JOIN shops s ON b.Shop_id = s.Id
        WHERE b.Id = %s
    """, (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    conn.close()

    if not booking:
        return "Booking not found."

    return render_template("booking_completed.html", booking=booking)


@app.route("/set_charge/<int:booking_id>", methods=["GET", "POST"])
def set_charge(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM booking
        WHERE Id = %s AND Professional_id = %s
    """, (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        return "Booking not found."

    if request.method == "POST":
        service_charge = float(request.form.get("service_charge") or request.form.get("charge") or 0)
        travel_charge = float(request.form.get("travel_charge", 0) or 0)
        final_charge = round(service_charge + travel_charge, 2)
        advance_paid = float(booking.get("advance_amount") or 0)
        remaining = max(0.0, round(final_charge - advance_paid, 2))

        cursor.execute("""
            UPDATE booking
            SET Charge = %s,
                Travel_charge = %s,
                remaining_amount = %s
            WHERE Id = %s AND Professional_id = %s
        """, (final_charge, travel_charge, remaining, booking_id, session["user_id"]))
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Final charges saved! Service: ₹{service_charge} + Travel: ₹{travel_charge} = Total: ₹{final_charge}. (Advance token ₹{advance_paid} deducted. Customer remaining due: ₹{remaining})")
        return redirect(url_for("booking_requests"))

    cursor.close()
    conn.close()
    return render_template("set_charge.html", booking=booking)


@app.route("/add_review/<int:booking_id>", methods=["GET", "POST"])
def add_review(booking_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("user_type") != "customer":
        return redirect(url_for("home"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM booking
        WHERE Id = %s AND Customer_id = %s AND Status = 'completed'
    """, (booking_id, session["user_id"]))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        flash("Only completed bookings can be reviewed.")
        return redirect(url_for("my_bookings"))

    if request.method == "POST":
        rating = int(request.form["rating"])
        review = request.form["review"].strip()

        cursor.execute("""
            INSERT INTO reviews
            (Booking_id, Customer_id, Professional_id, Rating, Review)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            booking["Id"],
            session["user_id"],
            booking["Professional_id"],
            rating,
            review
        ))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Thank you! Your review has been submitted.")
        return redirect(url_for("my_bookings"))

    cursor.close()
    conn.close()
    return render_template("add_review.html", booking=booking)


# -------------------------------------------------------------
# Job Need Portal (Kaam Ki Zaroorat / Job Seeker & Hiring)
# -------------------------------------------------------------

@app.route("/jobs")
def jobs():
    category = request.args.get("category", "").strip()
    city = request.args.get("city", "").strip()
    post_type = request.args.get("post_type", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # ONLY show job offers posted by verified shop owners / studios
    query = """
        SELECT jp.*, s.Shop_name, s.Owner_name, s.City as shop_city, s.Address as shop_address, s.Phone as shop_phone
        FROM job_posts jp
        JOIN shops s ON jp.user_id = s.User_id
        JOIN users u ON jp.user_id = u.Id AND u.User_type = 'professional'
        WHERE jp.status = 'open'
    """
    params = []

    if post_type:
        query += " AND jp.post_type = %s"
        params.append(post_type)

    if category:
        query += " AND jp.category = %s"
        params.append(category)

    if city:
        query += " AND (jp.city LIKE %s OR s.City LIKE %s)"
        params.extend([f"%{city}%", f"%{city}%"])

    if search:
        query += " AND (jp.title LIKE %s OR jp.description LIKE %s OR jp.skills_required LIKE %s OR s.Shop_name LIKE %s)"
        s = f"%{search}%"
        params.extend([s, s, s, s])

    query += " ORDER BY jp.id DESC"
    cursor.execute(query, tuple(params))
    job_posts = cursor.fetchall()

    # Distinct categories and cities for filters from shop owner job offers
    cursor.execute("""
        SELECT DISTINCT jp.category 
        FROM job_posts jp
        JOIN shops s ON jp.user_id = s.User_id
        WHERE jp.category != ''
    """)
    categories = [r["category"] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT DISTINCT jp.city 
        FROM job_posts jp
        JOIN shops s ON jp.user_id = s.User_id
        WHERE jp.city != ''
    """)
    cities = [r["city"] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template(
        "jobs.html",
        jobs=job_posts,
        selected_type=post_type,
        selected_cat=category,
        selected_city=city,
        search=search,
        categories=categories,
        cities=cities
    )


@app.route("/jobs/post", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session:
        flash("Please login as a shop owner to post a job offer.")
        return redirect(url_for("login"))

    if session.get("user_type") != "professional":
        flash("Job posting is exclusively for registered Shop Owners looking to hire skilled workers. Browse active opportunities below!")
        return redirect(url_for("jobs"))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM shops WHERE User_id = %s", (user_id,))
    shop = cursor.fetchone()

    if not shop:
        cursor.close()
        conn.close()
        flash("Please set up your shop profile first before posting a job offer.")
        return redirect(url_for("shop_profile"))

    if request.method == "POST":
        post_type = "need_worker"
        title = request.form["title"].strip()
        category = request.form["category"].strip()
        description = request.form["description"].strip()
        skills_required = request.form.get("skills_required", "").strip()
        salary = request.form.get("salary", "").strip()
        commission_percentage = request.form.get("commission_percentage", "").strip()
        working_hours = request.form.get("working_hours", "").strip()
        budget = request.form.get("budget", "").strip() or salary
        location = request.form.get("location", shop.get("Address", "")).strip()
        city = request.form.get("city", shop.get("City", "")).strip()
        contact_name = request.form.get("contact_name", shop.get("Owner_name", "")).strip()
        contact_phone = request.form.get("contact_phone", shop.get("Phone", "")).strip()

        cursor.execute("""
            INSERT INTO job_posts
            (user_id, post_type, title, category, description, skills_required, budget, salary, commission_percentage, working_hours, location, city, contact_name, contact_phone, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open')
        """, (
            user_id, post_type, title, category, description, skills_required,
            budget, salary, commission_percentage, working_hours,
            location, city, contact_name, contact_phone
        ))
        conn.commit()
        cursor.close()
        conn.close()

        flash(f"Job offer for '{shop['Shop_name']}' published successfully! It is now live on the Job Need Portal.")
        return redirect(url_for("jobs"))

    cursor.close()
    conn.close()
    return render_template("post_job.html", shop=shop)


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT jp.*, s.Shop_name, s.Owner_name, s.City as shop_city, s.Address as shop_address, s.Phone as shop_phone
        FROM job_posts jp
        LEFT JOIN shops s ON jp.user_id = s.User_id
        WHERE jp.id = %s
    """, (job_id,))
    job = cursor.fetchone()

    if not job:
        cursor.close()
        conn.close()
        flash("Job post not found.")
        return redirect(url_for("jobs"))

    # If the creator is viewing, load applicants
    applicants = []
    has_applied = False
    user_id = session.get("user_id")

    if user_id:
        if user_id == job["user_id"]:
            cursor.execute("""
                SELECT * FROM job_applications
                WHERE job_id = %s
                ORDER BY id DESC
            """, (job_id,))
            applicants = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT id FROM job_applications
                WHERE job_id = %s AND applicant_id = %s
            """, (job_id, user_id))
            has_applied = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    return render_template(
        "job_detail.html",
        job=job,
        applicants=applicants,
        has_applied=has_applied
    )


@app.route("/jobs/apply/<int:job_id>", methods=["POST"])
def apply_job(job_id):
    if "user_id" not in session:
        flash("Please login to apply for this job.")
        return redirect(url_for("login"))

    applicant_id = session["user_id"]
    applicant_name = request.form["applicant_name"].strip()
    applicant_phone = request.form["applicant_phone"].strip()
    experience_years = request.form.get("experience_years", "").strip()
    message = request.form.get("message", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO job_applications
        (job_id, applicant_id, applicant_name, applicant_phone, experience_years, message, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'applied')
    """, (
        job_id, applicant_id, applicant_name, applicant_phone, experience_years, message
    ))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Your job application has been submitted successfully! The employer will contact you.")
    return redirect(url_for("job_detail", job_id=job_id))


@app.route("/my_jobs")
def my_jobs():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT j.*,
               (SELECT COUNT(*) FROM job_applications WHERE job_id = j.id) as applicant_count
        FROM job_posts j
        WHERE j.user_id = %s
        ORDER BY j.id DESC
    """, (user_id,))
    my_posts = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("my_jobs.html", posts=my_posts)


@app.route("/jobs/toggle_status/<int:job_id>")
def toggle_job_status(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM job_posts WHERE id = %s AND user_id = %s", (job_id, session["user_id"]))
    job = cursor.fetchone()

    if job:
        new_status = "closed" if job["status"] == "open" else "open"
        cursor.execute("UPDATE job_posts SET status = %s WHERE id = %s", (new_status, job_id))
        conn.commit()
        flash(f"Job status updated to {new_status}.")

    cursor.close()
    conn.close()
    return redirect(url_for("my_jobs"))


@app.route("/jobs/delete/<int:job_id>")
def delete_job(job_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_posts WHERE id = %s AND user_id = %s", (job_id, session["user_id"]))
    cursor.execute("DELETE FROM job_applications WHERE job_id = %s", (job_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Job post deleted successfully.")
    return redirect(url_for("my_jobs"))


# -------------------------------------------------------------
# Admin Registration, Login & Central Management
# -------------------------------------------------------------

@app.route("/admin/register", methods=["GET", "POST"])
@app.route("/admin/signup", methods=["GET", "POST"])
def admin_register():
    if session.get("is_admin") or session.get("user_type") == "admin":
        return redirect(url_for("admin"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        secret_key = request.form.get("secret_key", "").strip()

        if secret_key not in ["admin123", "admin", "servicehub@2026", "servicehub_admin"]:
            flash("Invalid Administrator Security Key! Enrollment requires verified master passcode.")
            return render_template("admin_register.html")

        if not name or not email or not password or not phone:
            flash("Please fill in all required fields.")
            return render_template("admin_register.html")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COALESCE(MAX(Admin_no), 0) + 1 AS next_no FROM users WHERE User_type = 'admin'")
            row = cursor.fetchone()
            admin_no = row["next_no"] if row else 1
            cursor.execute("""
                INSERT INTO users (Name, Email, Phone, Password, User_type, Admin_no)
                VALUES (%s, %s, %s, %s, 'admin', %s)
            """, (name, email, phone, password, admin_no))
            conn.commit()
            flash("Administrator profile registered successfully! Please login with your admin credentials.")
            return redirect(url_for("admin_login"))
        except mysql.connector.Error as err:
            flash(f"Administrator registration failed: {err}")
        finally:
            cursor.close()
            conn.close()

    return render_template("admin_register.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin") or session.get("user_type") == "admin":
        return redirect(url_for("admin"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        passcode = request.form.get("passcode", "").strip()

        # 1. Quick Passcode Login
        if passcode in ["admin123", "admin", "servicehub@2026"]:
            session["is_admin"] = True
            session["user_name"] = "Master Admin"
            session["user_type"] = "admin"
            flash("Admin authorization verified via master passcode. Command center unlocked.")
            return redirect(url_for("admin"))

        # 2. Registered Admin Account Login
        if email and password:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM users
                WHERE Email = %s AND Password = %s AND User_type = 'admin'
            """, (email, password))
            admin_user = cursor.fetchone()
            cursor.close()
            conn.close()

            if admin_user:
                session["is_admin"] = True
                session["user_id"] = admin_user["Id"]
                session["user_type"] = "admin"
                session["user_name"] = admin_user["Name"]
                session["user_email"] = admin_user["Email"]
                session["user_phone"] = admin_user["Phone"]
                flash(f"Welcome back Administrator {admin_user['Name']}! Command center unlocked.")
                return redirect(url_for("admin"))
            else:
                flash("Invalid Administrator email or password. Access denied.")
                return render_template("admin_login.html")

        flash("Please provide your Administrator credentials or authorization passcode.")

    return render_template("admin_login.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Passcode / Login authorization check
    is_authorized = bool(session.get("is_admin") or session.get("user_type") == "admin")

    if not is_authorized:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            passcode = request.form.get("passcode", "").strip()

            if passcode in ["admin123", "admin", "servicehub@2026"]:
                session["is_admin"] = True
                session["user_name"] = "Master Admin"
                session["user_type"] = "admin"
                flash("Admin authorization verified via passcode.")
                return redirect(url_for("admin"))

            if email and password:
                conn = get_db()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT * FROM users
                    WHERE Email = %s AND Password = %s AND User_type = 'admin'
                """, (email, password))
                admin_user = cursor.fetchone()
                cursor.close()
                conn.close()

                if admin_user:
                    session["is_admin"] = True
                    session["user_id"] = admin_user["Id"]
                    session["user_type"] = "admin"
                    session["user_name"] = admin_user["Name"]
                    session["user_email"] = admin_user["Email"]
                    session["user_phone"] = admin_user["Phone"]
                    flash(f"Welcome back Administrator {admin_user['Name']}!")
                    return redirect(url_for("admin"))

            flash("Invalid administrator credentials or passcode. Access denied.")
            return render_template("admin_dashboard.html", authorized=False)

        return render_template("admin_dashboard.html", authorized=False)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1. Summary Metrics
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE User_type = 'customer'")
    total_customers = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE User_type = 'professional'")
    total_professionals = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM shops")
    total_shops = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking")
    total_bookings = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Status = 'pending'")
    pending_bookings = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Status = 'accepted'")
    accepted_bookings = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM booking WHERE Status = 'completed'")
    completed_bookings = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COALESCE(SUM(advance_amount), 0) as total FROM booking WHERE payment_status IN ('advance_paid', 'fully_paid')")
    total_advance_volume = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as cnt FROM job_posts")
    total_jobs = cursor.fetchone()["cnt"]

    # 2. Customers Table
    cursor.execute("""
        SELECT u.Id, 
               COALESCE(u.Client_no, ROW_NUMBER() OVER (ORDER BY u.Id ASC)) as client_no,
               u.Name, u.Email, u.Phone, u.Created_at,
               (SELECT COUNT(*) FROM booking WHERE Customer_id = u.Id) as booking_count
        FROM users u
        WHERE u.User_type = 'customer'
        ORDER BY u.Id ASC
    """)
    customers = cursor.fetchall()

    # 3. Professionals Table
    cursor.execute("""
        SELECT u.Id as user_id, 
               COALESCE(u.Pro_no, DENSE_RANK() OVER (ORDER BY u.Id ASC)) as pro_no,
               u.Name, u.Email, u.Phone,
               s.Id as shop_id, s.Shop_name, s.City, s.State, s.upi_id, s.qr_code,
               COALESCE(ROUND(AVG(r.Rating), 1), 5.0) as avg_rating,
               COUNT(r.Id) as review_count
        FROM users u
        LEFT JOIN shops s ON u.Id = s.User_id
        LEFT JOIN reviews r ON u.Id = r.Professional_id
        WHERE u.User_type = 'professional'
        GROUP BY u.Id, s.Id
        ORDER BY u.Id ASC
    """)
    professionals = cursor.fetchall()

    # 4. All Bookings Table
    cursor.execute("""
        SELECT b.*,
               c.Name as customer_name, c.Phone as customer_phone,
               s.Shop_name, p.Name as pro_name
        FROM booking b
        LEFT JOIN users c ON b.Customer_id = c.Id
        LEFT JOIN shops s ON b.Shop_id = s.Id
        LEFT JOIN users p ON b.Professional_id = p.Id
        ORDER BY b.Id ASC
    """)
    all_bookings = cursor.fetchall()

    # 5. Marketplace Jobs
    cursor.execute("""
        SELECT j.*, s.Shop_name, s.Owner_name, s.Phone as shop_phone,
               (SELECT COUNT(*) FROM job_applications WHERE job_id = j.id) as applicant_count
        FROM job_posts j
        LEFT JOIN shops s ON j.user_id = s.User_id
        ORDER BY j.id ASC
    """)
    all_jobs = cursor.fetchall()

    # 6. Registered Administrators Table
    cursor.execute("""
        SELECT u.Id, 
               COALESCE(u.Admin_no, ROW_NUMBER() OVER (ORDER BY u.Id ASC)) as admin_no,
               u.Name, u.Email, u.Phone, u.Created_at
        FROM users u
        WHERE u.User_type = 'admin'
        ORDER BY u.Id ASC
    """)
    administrators = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        authorized=True,
        total_customers=total_customers,
        total_professionals=total_professionals,
        total_shops=total_shops,
        total_bookings=total_bookings,
        pending_bookings=pending_bookings,
        accepted_bookings=accepted_bookings,
        completed_bookings=completed_bookings,
        total_advance_volume=total_advance_volume,
        total_jobs=total_jobs,
        customers=customers,
        professionals=professionals,
        bookings=all_bookings,
        jobs=all_jobs,
        administrators=administrators
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    if session.get("user_type") == "admin":
        session.clear()
    flash("Admin session logged out safely.")
    return redirect(url_for("admin_login"))


@app.route("/admin/update_booking_status/<int:booking_id>/<string:new_status>")
def admin_update_booking_status(booking_id, new_status):
    if not (session.get("is_admin") or session.get("user_type") == "admin"):
        flash("Admin authorization required.")
        return redirect(url_for("admin_login"))

    if new_status not in ["pending", "accepted", "completed", "cancelled"]:
        flash("Invalid booking status.")
        return redirect(url_for("admin"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE booking SET Status = %s WHERE Id = %s", (new_status, booking_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Booking #{booking_id} status updated to {new_status.upper()} by Administrator.")
    return redirect(url_for("admin"))


@app.route("/admin/delete_booking/<int:booking_id>")
def admin_delete_booking(booking_id):
    if not (session.get("is_admin") or session.get("user_type") == "admin"):
        flash("Admin authorization required.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM booking WHERE Id = %s", (booking_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Booking #{booking_id} permanently removed by Administrator.")
    return redirect(url_for("admin"))


@app.route("/admin/toggle_job/<int:job_id>")
def admin_toggle_job(job_id):
    if not (session.get("is_admin") or session.get("user_type") == "admin"):
        flash("Admin authorization required.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM job_posts WHERE id = %s", (job_id,))
    job = cursor.fetchone()

    if job:
        new_status = "closed" if job["status"] == "open" else "open"
        cursor.execute("UPDATE job_posts SET status = %s WHERE id = %s", (new_status, job_id))
        conn.commit()
        flash(f"Job Offer #{job_id} status updated to {new_status.upper()} by Admin.")

    cursor.close()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/admin/delete_job/<int:job_id>")
def admin_delete_job(job_id):
    if not (session.get("is_admin") or session.get("user_type") == "admin"):
        flash("Admin authorization required.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_posts WHERE id = %s", (job_id,))
    cursor.execute("DELETE FROM job_applications WHERE job_id = %s", (job_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Job Offer #{job_id} permanently deleted by Administrator.")
    return redirect(url_for("admin"))


@app.route("/admin/delete_user/<int:user_id>")
def admin_delete_user(user_id):
    if not (session.get("is_admin") or session.get("user_type") == "admin"):
        flash("Admin authorization required.")
        return redirect(url_for("admin_login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM job_applications WHERE applicant_id = %s", (user_id,))
    cursor.execute("DELETE FROM job_posts WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM reviews WHERE Customer_id = %s OR Professional_id = %s", (user_id, user_id))
    cursor.execute("DELETE FROM booking WHERE Customer_id = %s OR Professional_id = %s", (user_id, user_id))
    cursor.execute("DELETE FROM works WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM services WHERE user_id = %s", (user_id,))
    cursor.execute("DELETE FROM shops WHERE User_id = %s", (user_id,))
    cursor.execute("DELETE FROM users WHERE Id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"User #{user_id} and all related records successfully deleted by Administrator.")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)