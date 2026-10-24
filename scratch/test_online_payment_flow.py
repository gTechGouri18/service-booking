import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from app import app, get_db

# Reset test data
init_conn = get_db()
init_cur = init_conn.cursor()
init_cur.execute("DELETE FROM booking WHERE Customer_id IN (SELECT Id FROM users WHERE Email IN ('rahul@example.com', 'amit@example.com'))")
init_cur.execute("DELETE FROM services WHERE user_id IN (SELECT Id FROM users WHERE Email IN ('rahul@example.com', 'amit@example.com'))")
init_cur.execute("DELETE FROM shops WHERE User_id IN (SELECT Id FROM users WHERE Email IN ('rahul@example.com', 'amit@example.com'))")
init_cur.execute("DELETE FROM users WHERE Email IN ('rahul@example.com', 'amit@example.com')")
init_conn.commit()
init_cur.close()
init_conn.close()

with app.test_client() as client:
    # 1. Register Professional
    r1 = client.post('/signup', data={
        'name': 'Rahul Sharma',
        'email': 'rahul@example.com',
        'phone': '9876543210',
        'password': 'password123',
        'user_type': 'professional'
    }, follow_redirects=True)
    assert r1.status_code == 200
    print('1. Registered Professional: Rahul Sharma')

    # Login Professional
    client.post('/login', data={'email': 'rahul@example.com', 'password': 'password123'}, follow_redirects=True)

    # Setup Shop
    r_shop = client.post('/shop_profile', data={
        'shop_name': 'Sharma Electricals & AC Service',
        'owner_name': 'Rahul Sharma',
        'phone': '9876543210',
        'address': 'Station Road, Sector 1',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'service_area': 'Bhilai, Durg, Raipur',
        'work_details': 'All electrical repair, AC installation, wiring and switchboard replacement.',
        'other_city_charge': '50',
        'other_state_charge': '150'
    }, follow_redirects=True)
    assert r_shop.status_code == 200
    print('2. Created Shop Profile: Sharma Electricals & AC Service')

    # Add Service
    r_serv = client.post('/my_services', data={
        'service_name': 'AC Servicing & Gas Refill',
        'category': 'Appliance',
        'price': '500',
        'description': 'Complete jet wash and gas pressure check'
    }, follow_redirects=True)
    assert r_serv.status_code == 200
    print('3. Added Service: AC Servicing (Rs 500)')

    # Logout Professional
    client.get('/logout', follow_redirects=True)

    # 2. Register Customer
    r_cust = client.post('/signup', data={
        'name': 'Amit Verma',
        'email': 'amit@example.com',
        'phone': '9123456789',
        'password': 'password123',
        'user_type': 'customer'
    }, follow_redirects=True)
    assert r_cust.status_code == 200
    print('4. Registered Customer: Amit Verma')

    # Login Customer
    client.post('/login', data={'email': 'amit@example.com', 'password': 'password123'}, follow_redirects=True)

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT Id FROM users WHERE Email = 'rahul@example.com'")
    prof_id = cur.fetchone()['Id']
    cur.execute("SELECT Id FROM users WHERE Email = 'amit@example.com'")
    cust_id = cur.fetchone()['Id']

    # Check Book Page GET
    r_book_page = client.get(f'/book/{prof_id}')
    assert r_book_page.status_code == 200
    assert b'PhonePe' in r_book_page.data
    assert b'Google Pay' in r_book_page.data
    assert b'Paytm' in r_book_page.data
    assert b'Net Banking' in r_book_page.data
    print(f'5. GET /book/{prof_id} contains PhonePe, Google Pay, Paytm, Net Banking UI options')

    # Submit Booking with 20% advance via PhonePe UPI
    # Service rate: 500, Travel: 0 (same city: Bhilai) => Total: 500
    # Advance (20%): 100, Remaining: 400
    r_book_post = client.post(f'/book/{prof_id}', data={
        'service': 'AC Servicing & Gas Refill',
        'estimated_price': '500',
        'service_type': 'home',
        'booking_date': '2026-10-01',
        'booking_time': '10:30',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'advance_percentage': '20',
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)
    assert r_book_post.status_code == 200
    print('6. Booking submitted successfully with PhonePe UPI advance!')

    # Verify DB record
    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Customer_id = %s', (cust_id,))
    b = cur.fetchone()
    print(f"Booking Record in DB: ID={b['Id']}, Charge={b['Charge']}, Advance={b['advance_amount']}, Remaining={b['remaining_amount']}, Status={b['Status']}, PaymentStatus={b['payment_status']}, Method={b['payment_method']}")
    assert float(b['Charge']) == 500.0
    assert float(b['advance_amount']) == 100.0
    assert float(b['remaining_amount']) == 400.0
    assert b['payment_status'] == 'advance_paid'
    assert b['payment_method'] == 'PhonePe UPI'

    # Customer View Bookings
    r_my_bookings = client.get('/my_bookings')
    assert b'PhonePe UPI' in r_my_bookings.data or b'Advance Paid' in r_my_bookings.data
    print('7. My Bookings shows Advance Paid badge!')

    # Logout Customer & Login Professional to Accept & Complete Booking
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'rahul@example.com', 'password': 'password123'}, follow_redirects=True)

    # Accept Booking
    r_accept = client.get(f"/accept_booking/{b['Id']}", follow_redirects=True)
    assert r_accept.status_code == 200
    print('8. Professional accepted the booking')

    # Set Final Charge (e.g. 500)
    r_charge = client.post(f"/set_charge/{b['Id']}", data={'charge': '500'}, follow_redirects=True)
    assert r_charge.status_code == 200
    print('9. Professional confirmed final charge Rs 500')

    # Complete Booking
    r_comp = client.get(f"/complete_booking/{b['Id']}", follow_redirects=True)
    assert r_comp.status_code == 200
    print('10. Professional marked booking as completed!')

    # Logout Professional & Login Customer to Pay Remaining Balance via Google Pay
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'amit@example.com', 'password': 'password123'}, follow_redirects=True)

    # Customer visits booking_completed page
    r_comp_view = client.get(f"/booking_completed/{b['Id']}")
    assert b'Immediate Settlement Required' in r_comp_view.data
    assert b'PhonePe' in r_comp_view.data
    assert b'Google Pay' in r_comp_view.data
    print('11. Customer sees Immediate Settlement with PhonePe and Google Pay options!')

    # Customer pays remaining balance of Rs 400 via Google Pay
    r_pay_rem = client.post(f"/pay_remaining/{b['Id']}", data={
        'payment_method': 'Google Pay (GPay)'
    }, follow_redirects=True)
    assert r_pay_rem.status_code == 200
    print('12. Customer successfully paid remaining balance via Google Pay (GPay)!')

    # Verify DB record is fully paid
    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (b['Id'],))
    b_updated = cur.fetchone()
    print(f"Updated DB Record: PaymentStatus={b_updated['payment_status']}, Remaining={b_updated['remaining_amount']}, Method={b_updated['payment_method']}")
    assert b_updated['payment_status'] == 'fully_paid'
    assert float(b_updated['remaining_amount']) == 0.0
    assert b_updated['payment_method'] == 'Google Pay (GPay)'
    print('=== ALL ONLINE PAYMENT TEST SCENARIOS PASSED 100%! ===')

    conn.close()
