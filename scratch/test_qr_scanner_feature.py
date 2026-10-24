import sys, os, io
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from app import app, get_db

# 1. Clean up test users
conn = get_db()
cur = conn.cursor(dictionary=True)
cur.execute("DELETE FROM booking WHERE Customer_id IN (SELECT Id FROM users WHERE Email IN ('proftest@example.com', 'custtest@example.com'))")
cur.execute("DELETE FROM services WHERE user_id IN (SELECT Id FROM users WHERE Email IN ('proftest@example.com', 'custtest@example.com'))")
cur.execute("DELETE FROM shops WHERE User_id IN (SELECT Id FROM users WHERE Email IN ('proftest@example.com', 'custtest@example.com'))")
cur.execute("DELETE FROM users WHERE Email IN ('proftest@example.com', 'custtest@example.com')")
conn.commit()

with app.test_client() as client:
    # 2. Register Professional
    r_reg = client.post('/signup', data={
        'name': 'Vikram Singh',
        'email': 'proftest@example.com',
        'phone': '9876500001',
        'password': 'password123',
        'user_type': 'professional'
    }, follow_redirects=True)
    assert r_reg.status_code == 200
    print('1. Registered Professional: Vikram Singh')

    client.post('/login', data={'email': 'proftest@example.com', 'password': 'password123'}, follow_redirects=True)

    # Fetch prof user id
    conn.commit()
    cur.execute("SELECT Id FROM users WHERE Email = 'proftest@example.com'")
    prof_id = cur.fetchone()['Id']

    # 3. Create Shop Profile with QR Code Image Upload and UPI ID
    # 1x1 transparent PNG byte stream for test
    dummy_png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00'
        b'\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    qr_data = (io.BytesIO(dummy_png), 'test_phonepe_qr.png')

    r_shop = client.post('/shop_profile', data={
        'shop_name': 'Vikram Home Services & AC',
        'owner_name': 'Vikram Singh',
        'phone': '9876500001',
        'address': 'Main Market, Nehru Nagar',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'service_area': 'Bhilai, Durg',
        'work_details': 'AC Repair, Jet Servicing, Inverter setup',
        'other_city_charge': '50',
        'other_state_charge': '150',
        'upi_id': 'vikram@okaxis',
        'qr_code': qr_data
    }, content_type='multipart/form-data', follow_redirects=True)
    assert r_shop.status_code == 200
    print('2. Shop Profile created with UPI ID and QR code image upload!')

    # Verify Shop Record in DB
    conn.commit()
    cur.execute("SELECT * FROM shops WHERE User_id = %s", (prof_id,))
    shop = cur.fetchone()
    assert shop is not None
    assert shop['upi_id'] == 'vikram@okaxis'
    assert 'qr_user_' in shop['qr_code']
    assert shop['qr_code'].endswith('test_phonepe_qr.png')
    print(f"3. DB Verification Passed: upi_id={shop['upi_id']}, qr_code={shop['qr_code']}")

    # Verify file saved on disk in static/uploads
    uploaded_path = os.path.join(app.static_folder, 'uploads', shop['qr_code'])
    assert os.path.exists(uploaded_path)
    print(f"4. File exists on disk at: {uploaded_path}")

    # Add Service
    client.post('/my_services', data={
        'service_name': 'Split AC Servicing',
        'category': 'Appliance',
        'price': '600',
        'description': 'Full split ac wash and inspection'
    }, follow_redirects=True)

    client.get('/logout', follow_redirects=True)

    # 4. Register Customer
    client.post('/signup', data={
        'name': 'Pooja Soni',
        'email': 'custtest@example.com',
        'phone': '9123400002',
        'password': 'password123',
        'user_type': 'customer'
    }, follow_redirects=True)

    client.post('/login', data={'email': 'custtest@example.com', 'password': 'password123'}, follow_redirects=True)
    conn.commit()
    cur.execute("SELECT Id FROM users WHERE Email = 'custtest@example.com'")
    cust_id = cur.fetchone()['Id']

    # 5. Customer visits /book/<prof_id>
    r_book_get = client.get(f'/book/{prof_id}')
    assert r_book_get.status_code == 200
    assert b'Official Scanner QR' in r_book_get.data
    assert shop['qr_code'].encode() in r_book_get.data
    assert b'vikram@okaxis' in r_book_get.data
    print('5. Customer Booking page correctly renders Professional QR Code image and UPI ID!')

    # 6. Customer Books service with 20% advance
    # Price = 600, Travel = 0 => Total = 600, Advance = 120, Remaining = 480
    r_book_post = client.post(f'/book/{prof_id}', data={
        'service': 'Split AC Servicing',
        'estimated_price': '600',
        'service_type': 'home',
        'booking_date': '2026-10-10',
        'booking_time': '11:00',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'advance_percentage': '20',
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)
    assert r_book_post.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Customer_id = %s ORDER BY Id DESC LIMIT 1', (cust_id,))
    bk = cur.fetchone()
    assert float(bk['advance_amount']) == 120.0
    assert float(bk['remaining_amount']) == 480.0
    print(f"6. Booking placed: Advance=Rs {bk['advance_amount']}, Remaining=Rs {bk['remaining_amount']}")

    # 7. Professional accepts and completes
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'proftest@example.com', 'password': 'password123'}, follow_redirects=True)
    client.get(f"/accept_booking/{bk['Id']}", follow_redirects=True)
    client.post(f"/set_charge/{bk['Id']}", data={'charge': '600'}, follow_redirects=True)
    client.get(f"/complete_booking/{bk['Id']}", follow_redirects=True)
    print('7. Professional accepted and marked booking completed!')

    # 8. Customer views /booking_completed/<booking_id>
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'custtest@example.com', 'password': 'password123'}, follow_redirects=True)
    r_comp = client.get(f"/booking_completed/{bk['Id']}")
    assert r_comp.status_code == 200
    assert b'Official Payment Scanner' in r_comp.data
    assert shop['qr_code'].encode() in r_comp.data
    assert b'vikram@okaxis' in r_comp.data
    print('8. Customer Completion page shows Professional QR Code and UPI ID for Remaining payment!')

    # 9. Customer pays remaining balance
    r_pay = client.post(f"/pay_remaining/{bk['Id']}", data={
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)
    assert r_pay.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (bk['Id'],))
    bk_final = cur.fetchone()
    assert bk_final['payment_status'] == 'fully_paid'
    assert float(bk_final['remaining_amount']) == 0.0
    print('9. Bill fully paid & settled!')

    # Clean up test files and data
    if os.path.exists(uploaded_path):
        os.remove(uploaded_path)
    cur.execute("DELETE FROM booking WHERE Customer_id = %s", (cust_id,))
    cur.execute("DELETE FROM services WHERE user_id = %s", (prof_id,))
    cur.execute("DELETE FROM shops WHERE User_id = %s", (prof_id,))
    cur.execute("DELETE FROM users WHERE Id IN (%s, %s)", (prof_id, cust_id))
    conn.commit()
    print('10. Cleaned up test data & files successfully.')
    print('=== ALL PROFESSIONAL QR SCANNER TESTS PASSED 100%! ===')

conn.close()
