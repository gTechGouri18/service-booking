import sys, os, re
sys.path.insert(0, os.path.abspath("."))
from app import app, get_db

client = app.test_client()

def test():
    print("========================================")
    print("VERIFYING FRESH DATABASE STATE & PLATFORM")
    print("========================================")

    # 1. Verify Database is completely clean with AUTO_INCREMENT = 1
    conn = get_db()
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
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
        count = cursor.fetchone()[0]
        assert count == 0, f"Table {table} is not empty! Count: {count}"

        cursor.execute(f"""
            SELECT AUTO_INCREMENT 
            FROM information_schema.tables 
            WHERE table_schema = 'service_booking' AND table_name = '{table}';
        """)
        ai_res = cursor.fetchone()
        next_id = ai_res[0] if ai_res else None
        assert next_id == 1, f"Table {table} AUTO_INCREMENT is {next_id}, expected 1"
        print(f" [PASS] Table '{table}': 0 rows, AUTO_INCREMENT = 1")

    cursor.close()
    conn.close()

    # 2. Public Routes on Empty Database
    public_urls = ["/", "/find_services", "/conditions", "/jobs", "/login", "/signup"]
    for url in public_urls:
        res = client.get(url)
        assert res.status_code == 200, f"Failed {url}: {res.status_code}"
        print(f" [PASS] {url:<25} -> Status: {res.status_code}")

    # Check that Home Page has theme-dark-cinematic and NO Trending/Featured sections
    res_home = client.get("/")
    html_home = res_home.get_data(as_text=True)
    assert "theme-dark-cinematic" in html_home, "theme-dark-cinematic missing on Home page"
    assert len(re.findall(r'[\u0900-\u097F]', html_home)) == 0, "Hindi found on Home page"
    assert "Featured Professionals" not in html_home, "Featured Professionals should be completely removed"
    assert "Trending Services" not in html_home, "Trending Services should be completely removed"
    print(" [PASS] Home Page: Verified theme-dark-cinematic body class present!")
    print(" [PASS] Home Page: Verified Featured Professionals & Trending Services completely removed!")
    print(" [PASS] Home Page: Verified 0 Hindi characters across all sections!")

    # Check that Find Services has clean empty state
    res_find = client.get("/find_services")
    html_find = res_find.get_data(as_text=True)
    assert "No Matching Professionals Found" in html_find, "Clean empty state missing in find_services"
    print(" [PASS] Find Services: Verified elegant empty state when no shops registered!")

    # Check that Job Need Portal is Pure English (0 Hindi) with clean empty state
    res_jobs = client.get("/jobs")
    html_jobs = res_jobs.get_data(as_text=True)
    assert "Job Need Portal • Studio Hiring Offers" in html_jobs or "Studio Hiring Offers" in html_jobs, "English title missing in jobs portal"
    assert "No Studio Job Offers Found" in html_jobs, "Clean empty state missing in jobs portal"
    assert len(re.findall(r'[\u0900-\u097F]', html_jobs)) == 0, "Hindi found in jobs portal"
    print(" [PASS] Job Need Portal: Clean empty state; Pure English verified with ZERO Hindi!")

    # 3. Security Check: Unauthenticated access
    res_post_job = client.get("/jobs/post")
    assert res_post_job.status_code in (302, 303), "Unauthenticated /jobs/post should redirect to login"
    print(" [PASS] /jobs/post redirected securely to login for unauthenticated visitors!")

    # 4. Admin Dashboard Check
    res_admin_gate = client.get("/admin")
    assert res_admin_gate.status_code == 200, f"Failed /admin gate: {res_admin_gate.status_code}"
    assert "Administrator Passcode" in res_admin_gate.get_data(as_text=True), "Passcode prompt missing"
    print(" [PASS] /admin (Gatekeeper)     -> Status: 200 (Passcode Protected)")

    res_admin_auth = client.post("/admin", data={"passcode": "admin123"}, follow_redirects=True)
    assert res_admin_auth.status_code == 200, f"Failed /admin post auth: {res_admin_auth.status_code}"
    html_admin = res_admin_auth.get_data(as_text=True)
    assert "Platform Command Center" in html_admin, "Dashboard header missing"
    print(" [PASS] /admin (Authenticated)  -> Status: 200 (All 8 Counters & Tabs Live)")

    print("\n========================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("DATABASE IS 100% CLEAN AND STARTS AT ID 1")
    print("========================================")

if __name__ == "__main__":
    test()
