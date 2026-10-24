import sys, os
sys.path.insert(0, os.path.abspath("."))
from app import app, get_db

client = app.test_client()

def test_all():
    print("==================================================")
    print("TESTING ADMIN REGISTRATION, LOGIN & HAIRSTYLE OPTION")
    print("==================================================")

    # 1. Verify Hairstyle option in templates
    with open("templates/my_services.html", "r", encoding="utf-8") as f:
        my_serv_content = f.read()
        assert '<option value="Hairstyle">💇 Hairstyle</option>' in my_serv_content, "Hairstyle missing in my_services.html"
        print(" [PASS] Hairstyle category option present in templates/my_services.html")

    with open("templates/post_job.html", "r", encoding="utf-8") as f:
        post_job_content = f.read()
        assert '<option value="Hairstyle">💇 Hairstyle</option>' in post_job_content, "Hairstyle missing in post_job.html"
        print(" [PASS] Hairstyle category option present in templates/post_job.html")

    with open("templates/jobs.html", "r", encoding="utf-8") as f:
        jobs_content = f.read()
        assert '<option value="Hairstyle"' in jobs_content, "Hairstyle missing in jobs.html"
        print(" [PASS] Hairstyle category option present in templates/jobs.html")

    # 2. Test Admin Register Page (GET)
    res_reg_get = client.get("/admin/register")
    assert res_reg_get.status_code == 200, f"Failed GET /admin/register: {res_reg_get.status_code}"
    assert "Register Administrator" in res_reg_get.get_data(as_text=True)
    print(" [PASS] GET /admin/register -> Status 200")

    # 3. Test Admin Register with invalid key (POST)
    res_reg_fail = client.post("/admin/register", data={
        "name": "Fake Admin",
        "email": "fake@servicehub.com",
        "phone": "9876543210",
        "password": "pass",
        "secret_key": "wrong_key"
    }, follow_redirects=True)
    assert res_reg_fail.status_code == 200
    assert "Invalid Administrator Security Key" in res_reg_fail.get_data(as_text=True)
    print(" [PASS] Invalid secret key rejected properly on /admin/register")

    # 4. Test Admin Register with valid key (POST)
    test_email = "superadmin@servicehub.com"
    # Ensure clean test state for test_email
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE Email = %s", (test_email,))
    conn.commit()
    c.close()
    conn.close()

    res_reg_success = client.post("/admin/register", data={
        "name": "Super Administrator",
        "email": test_email,
        "phone": "9988776655",
        "password": "adminsecretpassword",
        "secret_key": "admin123"
    }, follow_redirects=True)
    assert res_reg_success.status_code == 200
    assert "Administrator profile registered successfully" in res_reg_success.get_data(as_text=True)
    print(" [PASS] Valid Admin registered successfully! Redirected to /admin/login")

    # Verify user in database has User_type = 'admin'
    conn = get_db()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT * FROM users WHERE Email = %s", (test_email,))
    admin_row = c.fetchone()
    assert admin_row is not None, "Admin user not found in database"
    assert admin_row["User_type"] == "admin", f"Expected User_type='admin', got {admin_row['User_type']}"
    print(f" [PASS] DB Verification: User #{admin_row['Id']} ({admin_row['Name']}) has User_type = 'admin'")
    c.close()
    conn.close()

    # 5. Test Admin Login Page (GET)
    res_login_get = client.get("/admin/login")
    assert res_login_get.status_code == 200
    assert "Administrator Login" in res_login_get.get_data(as_text=True)
    print(" [PASS] GET /admin/login -> Status 200")

    # 6. Test Admin Login with registered credentials (POST)
    res_login_post = client.post("/admin/login", data={
        "email": test_email,
        "password": "adminsecretpassword"
    }, follow_redirects=True)
    assert res_login_post.status_code == 200
    html_dashboard = res_login_post.get_data(as_text=True)
    assert "Platform Command Center" in html_dashboard, "Dashboard header missing after admin login"
    assert "Registered Platform Administrators" in html_dashboard, "Administrators tab missing in dashboard"
    assert "Super Administrator" in html_dashboard, "Registered admin name missing in administrators table"
    print(" [PASS] POST /admin/login with email/password authenticated successfully and unlocked Command Center!")

    # 7. Test Admin Logout
    res_logout = client.get("/admin/logout", follow_redirects=True)
    assert res_logout.status_code == 200
    assert "Admin session logged out safely" in res_logout.get_data(as_text=True)
    print(" [PASS] GET /admin/logout safely logged out and cleared session!")

    # 8. Test Standard /login with Admin Credentials
    res_std_login = client.post("/login", data={
        "email": test_email,
        "password": "adminsecretpassword"
    }, follow_redirects=True)
    assert res_std_login.status_code == 200
    assert "Platform Command Center" in res_std_login.get_data(as_text=True)
    print(" [PASS] POST /login with Admin credentials automatically unlocked Command Center!")

    # Clean up test admin user so database is reset
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE Email = %s", (test_email,))
    conn.commit()
    c.close()
    conn.close()
    print(" [PASS] Cleaned up temporary test admin user")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_all()
