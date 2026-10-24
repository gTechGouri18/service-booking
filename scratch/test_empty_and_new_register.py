import sys, os
sys.path.insert(0, os.path.abspath("."))
from app import app, get_db

client = app.test_client()

def test_empty_state_and_first_registration():
    print("==================================================")
    print("TESTING EMPTY STATE & FIRST USER REGISTRATION (ID 1)")
    print("==================================================")

    # 1. Test pages load smoothly on empty database
    routes = ["/", "/find_services", "/jobs", "/login", "/signup", "/conditions"]
    for r in routes:
        res = client.get(r)
        assert res.status_code == 200, f"Route {r} failed with status {res.status_code}"
        print(f" [PASS] Route {r:<20} -> Status: 200 (Clean empty state)")

    # 2. Register first user (Professional)
    signup_data = {
        "name": "First Master Artisan",
        "email": "master1@example.com",
        "phone": "9876543210",
        "password": "password123",
        "user_type": "professional"
    }
    res_signup = client.post("/signup", data=signup_data, follow_redirects=False)
    assert res_signup.status_code in (302, 303), f"Signup failed: {res_signup.status_code}"
    print(" [PASS] /signup POST successful -> Redirects to login")

    # Verify user ID in database
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email = %s", ("master1@example.com",))
    user = cur.fetchone()
    assert user is not None, "User not found in database"
    assert user["Id"] == 1, f"Expected user ID to be 1, but got {user['Id']}"
    print(f" [PASS] User successfully registered with Id: {user['Id']} (Confirmed starting from 1!)")

    # 3. Login with new user
    login_data = {
        "email": "master1@example.com",
        "password": "password123"
    }
    res_login = client.post("/login", data=login_data, follow_redirects=True)
    assert res_login.status_code == 200
    print(" [PASS] Login successful with newly registered user!")

    # 4. Create shop profile
    with client.session_transaction() as sess:
        sess["user_id"] = user["Id"]
        sess["user_type"] = user["User_type"]
        sess["user_name"] = user["Name"]

    shop_data = {
        "shop_name": "Royal Crown Studio",
        "owner_name": "First Master Artisan",
        "phone": "9876543210",
        "address": "Civic Center, Sector 1",
        "city": "Bhilai",
        "state": "Chhattisgarh",
        "service_area": "Bhilai, Durg",
        "work_details": "Luxury Salon, Bridal & Groom Styling",
        "local_travel_charge": "150",
        "other_city_charge": "400",
        "other_state_charge": "1200",
        "upi_id": "royal@upi"
    }
    res_shop = client.post("/shop_profile", data=shop_data, follow_redirects=True)
    assert res_shop.status_code == 200
    cur.execute("SELECT * FROM shops WHERE User_id = %s", (user["Id"],))
    shop = cur.fetchone()
    assert shop is not None, "Shop not found"
    assert shop["Id"] == 1, f"Expected Shop ID to be 1, but got {shop['Id']}"
    print(f" [PASS] Shop successfully created with Id: {shop['Id']} (Confirmed starting from 1!)")

    # 5. Post a job offer from the new shop owner
    job_data = {
        "title": "Senior Hair Stylist Needed",
        "category": "Salon & Beauty",
        "description": "Looking for professional bridal hair stylist.",
        "skills_required": "Hair Styling, Coloring",
        "budget": "25000 / month",
        "location": "Civic Center",
        "city": "Bhilai",
        "contact_name": "First Master Artisan",
        "contact_phone": "9876543210"
    }
    res_job = client.post("/jobs/post", data=job_data, follow_redirects=True)
    assert res_job.status_code == 200

    conn2 = get_db()
    cur2 = conn2.cursor(dictionary=True)
    cur2.execute("SELECT * FROM job_posts WHERE user_id = %s", (user["Id"],))
    job = cur2.fetchone()
    assert job is not None, "Job post not found in database"
    assert job["id"] == 1, f"Expected Job ID to be 1, but got {job['id']}"
    print(f" [PASS] Job post successfully created with Id: {job['id']} (Confirmed starting from 1!)")
    cur2.close()
    conn2.close()

    # 6. Verify that it now shows on /jobs and Home Page
    res_jobs = client.get("/jobs")
    html_jobs = res_jobs.get_data(as_text=True)
    assert "Royal Crown Studio" in html_jobs
    print(" [PASS] Newly posted studio job offer appears in /jobs!")

    res_home = client.get("/")
    html_home = res_home.get_data(as_text=True)
    assert "Royal Crown Studio" in html_home
    print(" [PASS] Newly posted studio job offer appears on Home page!")

    cur.close()
    conn.close()

    print("==================================================")
    print("VERIFICATION COMPLETE: SYSTEM STARTS FRESH FROM ID 1!")
    print("==================================================")

if __name__ == "__main__":
    test_empty_state_and_first_registration()
