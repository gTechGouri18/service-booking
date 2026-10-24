import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from app import app, get_db

conn = get_db()
cur = conn.cursor(dictionary=True)
cur.execute("DELETE FROM booking WHERE Customer_id IN (SELECT Id FROM users WHERE Email IN ('proff_charge@test.com', 'cust_charge@test.com'))")
cur.execute("DELETE FROM services WHERE user_id IN (SELECT Id FROM users WHERE Email IN ('proff_charge@test.com', 'cust_charge@test.com'))")
cur.execute("DELETE FROM shops WHERE User_id IN (SELECT Id FROM users WHERE Email IN ('proff_charge@test.com', 'cust_charge@test.com'))")
cur.execute("DELETE FROM users WHERE Email IN ('proff_charge@test.com', 'cust_charge@test.com')")
conn.commit()

with app.test_client() as client:
    # 1. Register Professional
    client.post('/signup', data={
        'name': 'Pooja Electricals',
        'email': 'proff_charge@test.com',
        'phone': '9988776655',
        'password': 'password123',
        'user_type': 'professional'
    }, follow_redirects=True)

    client.post('/login', data={'email': 'proff_charge@test.com', 'password': 'password123'}, follow_redirects=True)
    conn.commit()
    cur.execute("SELECT Id FROM users WHERE Email = 'proff_charge@test.com'")
    prof_id = cur.fetchone()['Id']

    # 2. Setup Shop with local and other city travel charges
    client.post('/shop_profile', data={
        'shop_name': 'Pooja Home Tech',
        'owner_name': 'Pooja',
        'phone': '9988776655',
        'address': 'Civic Center',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'service_area': 'Bhilai, Durg',
        'work_details': 'Electrician & Home appliance',
        'local_travel_charge': '60',
        'other_city_charge': '120',
        'other_state_charge': '250',
        'upi_id': 'pooja@upi'
    }, follow_redirects=True)

    conn.commit()
    cur.execute("SELECT * FROM shops WHERE User_id = %s", (prof_id,))
    shop = cur.fetchone()
    assert float(shop['Local_travel_charge']) == 60.0
    print('1. Shop Profile saved with custom Local Travel Charge = Rs 60!')

    client.get('/logout', follow_redirects=True)

    # 3. Register Customer
    client.post('/signup', data={
        'name': 'Ramesh Kumar',
        'email': 'cust_charge@test.com',
        'phone': '9112233445',
        'password': 'password123',
        'user_type': 'customer'
    }, follow_redirects=True)

    client.post('/login', data={'email': 'cust_charge@test.com', 'password': 'password123'}, follow_redirects=True)
    conn.commit()
    cur.execute("SELECT Id FROM users WHERE Email = 'cust_charge@test.com'")
    cust_id = cur.fetchone()['Id']

    # 4. Book Service (Home service, local city: Bhilai)
    # Service estimate = 500, Travel = 60 => Total = 560
    # Advance (20%) = 112, Remaining = 448
    client.post(f'/book/{prof_id}', data={
        'service': 'Wiring & Switch Setup',
        'estimated_price': '500',
        'service_type': 'home',
        'booking_date': '2026-10-15',
        'booking_time': '12:00',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'advance_percentage': '20',
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Customer_id = %s ORDER BY Id DESC LIMIT 1', (cust_id,))
    bk = cur.fetchone()
    assert float(bk['Charge']) == 560.0
    assert float(bk['Travel_charge']) == 60.0
    assert float(bk['advance_amount']) == 112.0
    assert float(bk['remaining_amount']) == 448.0
    print(f"2. Booking created: Total=Rs {bk['Charge']} (Travel=Rs {bk['Travel_charge']}), Advance=Rs {bk['advance_amount']}")

    # 5. Professional logs in to manually add/update both service_charge and travel_charge!
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'proff_charge@test.com', 'password': 'password123'}, follow_redirects=True)

    # Professional opens set_charge page
    r_get_charge = client.get(f"/set_charge/{bk['Id']}")
    assert r_get_charge.status_code == 200
    assert b'service_charge' in r_get_charge.data
    assert b'travel_charge' in r_get_charge.data
    print('3. GET /set_charge contains inputs for both service_charge and travel_charge!')

    # Professional manually inputs: Service Charge = 450, Travel Charge = 80
    # Final Total = 450 + 80 = 530
    # Advance already paid = 112
    # Remaining due = 530 - 112 = 418
    r_post_charge = client.post(f"/set_charge/{bk['Id']}", data={
        'service_charge': '450',
        'travel_charge': '80'
    }, follow_redirects=True)
    assert r_post_charge.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (bk['Id'],))
    bk_updated = cur.fetchone()
    print(f"4. DB Check after professional update: Charge=Rs {bk_updated['Charge']}, Travel=Rs {bk_updated['Travel_charge']}, Remaining=Rs {bk_updated['remaining_amount']}")
    assert float(bk_updated['Charge']) == 530.0
    assert float(bk_updated['Travel_charge']) == 80.0
    assert float(bk_updated['remaining_amount']) == 418.0
    assert float(bk_updated['advance_amount']) == 112.0

    # 6. Professional completes booking
    client.get(f"/complete_booking/{bk['Id']}", follow_redirects=True)

    # 7. Customer views completion and pays remaining balance of 418
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'cust_charge@test.com', 'password': 'password123'}, follow_redirects=True)

    r_comp = client.get(f"/booking_completed/{bk['Id']}")
    assert b'418' in r_comp.data
    print('5. Customer sees correct remaining balance of Rs 418!')

    r_settle = client.post(f"/pay_remaining/{bk['Id']}", data={
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)
    assert r_settle.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (bk['Id'],))
    bk_settled = cur.fetchone()
    assert bk_settled['payment_status'] == 'fully_paid'
    assert float(bk_settled['remaining_amount']) == 0.0
    print('6. Customer paid remaining balance, booking fully settled!')

    # Cleanup
    cur.execute("DELETE FROM booking WHERE Customer_id = %s", (cust_id,))
    cur.execute("DELETE FROM shops WHERE User_id = %s", (prof_id,))
    cur.execute("DELETE FROM users WHERE Id IN (%s, %s)", (prof_id, cust_id))
    conn.commit()
    print('=== ALL CUSTOM SERVICE & TRAVEL CHARGE TESTS PASSED 100%! ===')

conn.close()
