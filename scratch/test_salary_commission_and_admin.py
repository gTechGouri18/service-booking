import sys, os
sys.path.insert(0, os.path.abspath("."))
from app import app, get_db
from scratch.clean_database import wipe_and_reset

client = app.test_client()

def test_full_workflow():
    print("==================================================================")
    print("TESTING S.NO 1, ID 1, SALARY, COMMISSION % & ADMIN MANAGEMENT")
    print("==================================================================")

    # Clean DB first
    wipe_and_reset()

    # 1. Register Professional (Should get User ID = 1, Shop ID = 1)
    pro_signup = {
        "name": "Arjun Sharma",
        "email": "arjun@studio.com",
        "phone": "9876543210",
        "password": "pass123",
        "user_type": "professional",
        "shop_name": "Royal Crown Luxury Studio"
    }
    res = client.post("/signup", data=pro_signup)
    assert res.status_code in (302, 303)

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email = %s", ("arjun@studio.com",))
    pro_user = cur.fetchone()
    assert pro_user["Id"] == 1, f"Expected Pro User ID 1, got {pro_user['Id']}"
    print(f" [PASS] Professional Registered with User ID: {pro_user['Id']}")

    cur.execute("SELECT * FROM shops WHERE User_id = %s", (pro_user["Id"],))
    shop = cur.fetchone()
    assert shop["Id"] == 1, f"Expected Shop ID 1, got {shop['Id']}"
    print(f" [PASS] Studio Profile Created with Shop ID: {shop['Id']}")

    # 2. Shop owner posts a job with base salary, commission %, and working hours
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_type"] = "professional"
        sess["user_name"] = "Arjun Sharma"

    job_data = {
        "title": "Senior Bridal Makeup Artist & Hair Stylist",
        "category": "Salon & Beauty",
        "description": "Looking for talented bridal specialist for luxury studio.",
        "skills_required": "Bridal Artistry, HD Makeup",
        "salary": "₹35,000 / month",
        "commission_percentage": "20% per completed client service",
        "working_hours": "10:00 AM – 7:30 PM (6 Days)",
        "location": "Civic Center",
        "city": "Bhilai",
        "contact_name": "Arjun Sharma",
        "contact_phone": "9876543210"
    }
    res_job = client.post("/jobs/post", data=job_data, follow_redirects=True)
    assert res_job.status_code == 200

    conn2 = get_db()
    cur2 = conn2.cursor(dictionary=True)
    cur2.execute("SELECT * FROM job_posts WHERE user_id = 1")
    job = cur2.fetchone()
    assert job["id"] == 1, f"Expected Job ID 1, got {job['id']}"
    assert job["salary"] == "₹35,000 / month"
    assert job["commission_percentage"] == "20% per completed client service"
    assert job["working_hours"] == "10:00 AM – 7:30 PM (6 Days)"
    print(f" [PASS] Shop Owner Job Offer Created with ID: {job['id']}")
    print(f"        -> Salary: {job['salary'].encode('ascii', 'ignore').decode()}")
    print(f"        -> Work Commission: {job['commission_percentage']}")
    print(f"        -> Working Hours: {job['working_hours']}")

    # Check on public jobs page
    res_jobs = client.get("/jobs")
    html_jobs = res_jobs.get_data(as_text=True)
    assert "₹35,000 / month" in html_jobs
    assert "20% per completed client service" in html_jobs
    print(" [PASS] Job Portal /jobs displays Salary and Work Incentive %!")

    # 3. Register Customer (Should get User ID = 2)
    cust_signup = {
        "name": "Pooja Verma",
        "email": "pooja@client.com",
        "phone": "9123456780",
        "password": "pass123",
        "user_type": "customer"
    }
    client.post("/signup", data=cust_signup)
    conn_cust = get_db()
    cur_cust = conn_cust.cursor(dictionary=True)
    cur_cust.execute("SELECT * FROM users WHERE email = %s", ("pooja@client.com",))
    cust_user = cur_cust.fetchone()
    assert cust_user is not None, "Customer user not found"
    assert cust_user["Id"] == 2
    print(f" [PASS] Customer Registered with User ID: {cust_user['Id']}")
    cur_cust.close()
    conn_cust.close()

    # 4. Customer Books Service -> Booking ID must be 1!
    with client.session_transaction() as sess:
        sess["user_id"] = 2
        sess["user_type"] = "customer"
        sess["user_name"] = "Pooja Verma"
        sess["user_phone"] = "9123456780"

    book_data = {
        "service": "Luxury Bridal Glow & Styling",
        "service_type": "home",
        "booking_date": "2026-10-25",
        "booking_time": "11:00",
        "city": "Bhilai",
        "state": "Chhattisgarh",
        "estimated_price": "2500"
    }
    res_book = client.post("/book/1", data=book_data, follow_redirects=True)
    assert res_book.status_code == 200

    conn3 = get_db()
    cur3 = conn3.cursor(dictionary=True)
    cur3.execute("SELECT * FROM booking WHERE Customer_id = 2")
    booking = cur3.fetchone()
    assert booking["Id"] == 1, f"Expected Booking ID 1, got {booking['Id']}"
    print(f" [PASS] Booking Created with Booking ID: #{booking['Id']} (Confirmed starts at ID 1!)")

    # Check /my_bookings for S.No. and Booking ID
    res_my_b = client.get("/my_bookings")
    html_my_b = res_my_b.get_data(as_text=True)
    assert "#1" in html_my_b
    print(" [PASS] /my_bookings displays S.No. 1 and Booking ID #1!")

    # 5. Admin Management Tests
    with client.session_transaction() as sess:
        sess["is_admin"] = True

    res_admin = client.get("/admin")
    html_admin = res_admin.get_data(as_text=True)
    assert "Platform Command Center" in html_admin
    assert "#1" in html_admin
    assert "Royal Crown Luxury Studio" in html_admin
    print(" [PASS] Admin Dashboard displays S.No. 1, Booking ID #1, and Studio Name!")

    # Test Admin updating booking status to 'accepted'
    res_status = client.get("/admin/update_booking_status/1/accepted", follow_redirects=True)
    assert res_status.status_code == 200

    conn_admin = get_db()
    cur_admin = conn_admin.cursor(dictionary=True)
    cur_admin.execute("SELECT Status FROM booking WHERE Id = 1")
    b_updated = cur_admin.fetchone()
    assert b_updated["Status"] == "accepted", f"Expected accepted, got {b_updated['Status']}"
    print(" [PASS] Admin successfully updated booking status to ACCEPTED!")

    # Test Admin toggling job status
    res_toggle = client.get("/admin/toggle_job/1", follow_redirects=True)
    assert res_toggle.status_code == 200

    conn_admin.commit()
    cur_admin.execute("SELECT status FROM job_posts WHERE id = 1")
    j_updated = cur_admin.fetchone()
    assert j_updated["status"] == "closed"
    print(" [PASS] Admin successfully toggled job offer status to CLOSED!")

    cur_admin.close()
    conn_admin.close()

    cur.close()
    conn.close()
    cur2.close()
    conn2.close()
    cur3.close()
    conn3.close()

    # Final clean of DB so user gets completely fresh system starting at ID 1
    print("\nCleaning test records to leave database 100% fresh for user...")
    wipe_and_reset()

    print("==================================================================")
    print("ALL TESTS PASSED! DATABASE WIPE CONFIRMED & STARTS AT ID 1!")
    print("==================================================================")

if __name__ == "__main__":
    test_full_workflow()
