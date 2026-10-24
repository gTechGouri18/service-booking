import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from app import app, get_db

with app.test_client() as client:
    # Login customer
    client.post('/login', data={'email': 'amit@example.com', 'password': 'password123'}, follow_redirects=True)

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT Id FROM users WHERE Email = 'rahul@example.com'")
    prof_id = cur.fetchone()['Id']
    cur.execute("SELECT Id FROM users WHERE Email = 'amit@example.com'")
    cust_id = cur.fetchone()['Id']

    # Test Case 1: Customer Cancels
    client.post(f'/book/{prof_id}', data={
        'service': 'Wiring Repair',
        'estimated_price': '400',
        'service_type': 'home',
        'booking_date': '2026-10-02',
        'booking_time': '14:00',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'advance_percentage': '20',
        'payment_method': 'Google Pay (GPay)'
    }, follow_redirects=True)

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Customer_id = %s ORDER BY Id DESC LIMIT 1', (cust_id,))
    b1 = cur.fetchone()
    assert float(b1['advance_amount']) == 80.0
    print(f"Customer booked #b1 (ID: {b1['Id']}) with Advance 20% = Rs 80 via GPay")

    # Customer cancels
    r_cancel = client.get(f"/customer_cancel_booking/{b1['Id']}", follow_redirects=True)
    assert r_cancel.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (b1['Id'],))
    b1_cancelled = cur.fetchone()
    assert b1_cancelled['Status'] == 'cancelled'
    assert b1_cancelled['cancelled_by'] == 'customer'
    assert b1_cancelled['payment_status'] == 'non_refundable'
    print(f"Verified: Customer cancelled -> advance is NON-REFUNDABLE! (Status={b1_cancelled['Status']}, PaymentStatus={b1_cancelled['payment_status']}, CancelledBy={b1_cancelled['cancelled_by']})")

    # Test Case 2: Professional Cancels
    # Customer books another service
    client.post(f'/book/{prof_id}', data={
        'service': 'Switchboard Setup',
        'estimated_price': '300',
        'service_type': 'home',
        'booking_date': '2026-10-03',
        'booking_time': '16:00',
        'city': 'Bhilai',
        'state': 'Chhattisgarh',
        'advance_percentage': '20',
        'payment_method': 'PhonePe UPI'
    }, follow_redirects=True)

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Customer_id = %s ORDER BY Id DESC LIMIT 1', (cust_id,))
    b2 = cur.fetchone()
    print(f"Customer booked #b2 (ID: {b2['Id']}) with Advance 20% = Rs 60 via PhonePe")

    # Logout customer, login professional
    client.get('/logout', follow_redirects=True)
    client.post('/login', data={'email': 'rahul@example.com', 'password': 'password123'}, follow_redirects=True)

    # Professional cancels booking
    r_shop_cancel = client.get(f"/cancel_booking/{b2['Id']}", follow_redirects=True)
    assert r_shop_cancel.status_code == 200

    conn.commit()
    cur.execute('SELECT * FROM booking WHERE Id = %s', (b2['Id'],))
    b2_cancelled = cur.fetchone()
    assert b2_cancelled['Status'] == 'cancelled'
    assert b2_cancelled['cancelled_by'] == 'professional'
    assert b2_cancelled['payment_status'] == 'refunded'
    print(f"Verified: Professional cancelled -> 100% REFUNDED! (Status={b2_cancelled['Status']}, PaymentStatus={b2_cancelled['payment_status']}, CancelledBy={b2_cancelled['cancelled_by']})")

    print('=== ALL CANCELLATION POLICIES VERIFIED SUCCESSFULLY! ===')
    conn.close()
