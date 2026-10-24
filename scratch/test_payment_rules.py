from app import app, get_db

client = app.test_client()

conn = get_db()
cur = conn.cursor()
cur.execute('DELETE FROM reviews')
cur.execute('DELETE FROM booking')
cur.execute('DELETE FROM services')
cur.execute('DELETE FROM works')
cur.execute('DELETE FROM job_applications')
cur.execute('DELETE FROM job_posts')
cur.execute('DELETE FROM shops')
cur.execute('DELETE FROM users')
cur.execute('ALTER TABLE users AUTO_INCREMENT = 1')
cur.execute('ALTER TABLE shops AUTO_INCREMENT = 1')
cur.execute('ALTER TABLE booking AUTO_INCREMENT = 1')

# 1. Create Professional User & Shop
cur.execute("""
    INSERT INTO users (Name, Email, Phone, Password, User_type)
    VALUES ('G Gouri', 'gouri@example.com', '9202745205', 'Gouri123', 'professional')
""")
cur.execute("""
    INSERT INTO shops (User_id, Shop_name, Owner_name, Phone, Address, City, State, Service_area, Work_details, Other_city_charge, Other_state_charge)
    VALUES (1, 'Styles Hair Studio', 'Gouri', '9202745205', 'Sec 11', 'Bhilai', 'Chhattisgarh', 'Bhilai', 'Beauty Services', 500, 1500)
""")

# 2. Create Customer User
cur.execute("""
    INSERT INTO users (Name, Email, Phone, Password, User_type)
    VALUES ('Chinni', 'chinni@example.com', '9876543210', 'Chinni123', 'customer')
""")
conn.commit()

book_data = {
    'service': 'Hair Styling',
    'service_type': 'home',
    'booking_date': '2026-10-01',
    'booking_time': '14:00',
    'city': 'Bhilai',
    'state': 'Chhattisgarh',
    'estimated_price': '500',
    'advance_percentage': '20',
    'payment_method': 'UPI'
}

# --- TEST CASE 1: Customer Cancels -> Advance is NON-REFUNDABLE ---
with client.session_transaction() as sess:
    sess['user_id'] = 2
    sess['user_type'] = 'customer'
    sess['user_name'] = 'Chinni'

client.post('/book/1', data=book_data, follow_redirects=True)
client.get('/customer_cancel_booking/1', follow_redirects=True)

conn.commit()
cur = conn.cursor(dictionary=True)
cur.execute('SELECT * FROM booking WHERE Id = 1')
b1 = cur.fetchone()
print('CASE 1 (Customer Cancel):', b1['Status'], '| Cancelled by:', b1['cancelled_by'], '| Payment:', b1['payment_status'], '| Refund:', b1['refund_status'])
assert b1['Status'] == 'cancelled'
assert b1['cancelled_by'] == 'customer'
assert b1['payment_status'] == 'non_refundable'
assert 'Non-Refundable' in b1['refund_status']

# --- TEST CASE 2: Professional Cancels -> Advance is 100% REFUNDED ---
with client.session_transaction() as sess:
    sess['user_id'] = 2
    sess['user_type'] = 'customer'
    sess['user_name'] = 'Chinni'

client.post('/book/1', data=book_data, follow_redirects=True)

with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_type'] = 'professional'
    sess['user_name'] = 'G Gouri'

client.get('/cancel_booking/2', follow_redirects=True)

conn.commit()
cur.execute('SELECT * FROM booking WHERE Id = 2')
b2 = cur.fetchone()
print('CASE 2 (Shop Cancel):', b2['Status'], '| Cancelled by:', b2['cancelled_by'], '| Payment:', b2['payment_status'], '| Refund:', b2['refund_status'])
assert b2['Status'] == 'cancelled'
assert b2['cancelled_by'] == 'professional'
assert b2['payment_status'] == 'refunded'
assert '100% Refunded' in b2['refund_status']

# --- TEST CASE 3: Complete Booking -> Immediate Remaining Payment ---
with client.session_transaction() as sess:
    sess['user_id'] = 2
    sess['user_type'] = 'customer'
    sess['user_name'] = 'Chinni'

client.post('/book/1', data=book_data, follow_redirects=True)

with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['user_type'] = 'professional'
    sess['user_name'] = 'G Gouri'

client.get('/accept_booking/3', follow_redirects=True)
client.get('/complete_booking/3', follow_redirects=True)

conn.commit()
cur.execute('SELECT * FROM booking WHERE Id = 3')
b3 = cur.fetchone()
print('CASE 3 (Work Completed):', b3['Status'], '| Advance:', b3['advance_amount'], '| Remaining Due:', b3['remaining_amount'])
assert b3['Status'] == 'completed'
assert float(b3['remaining_amount']) == 400.0

# Customer pays remaining balance immediately
with client.session_transaction() as sess:
    sess['user_id'] = 2
    sess['user_type'] = 'customer'
    sess['user_name'] = 'Chinni'

client.post('/pay_remaining/3', follow_redirects=True)

conn.commit()
cur.execute('SELECT * FROM booking WHERE Id = 3')
b3_final = cur.fetchone()
print('CASE 3 (Fully Paid):', b3_final['Status'], '| Payment:', b3_final['payment_status'], '| Remaining:', b3_final['remaining_amount'])
assert b3_final['payment_status'] == 'fully_paid'
assert float(b3_final['remaining_amount']) == 0.0

# Reset DB clean
cur = conn.cursor()
cur.execute('DELETE FROM booking')
cur.execute('DELETE FROM shops')
cur.execute('DELETE FROM users')
cur.execute('ALTER TABLE users AUTO_INCREMENT = 1')
cur.execute('ALTER TABLE shops AUTO_INCREMENT = 1')
cur.execute('ALTER TABLE booking AUTO_INCREMENT = 1')
conn.commit()
cur.close()
conn.close()

print('ALL 3 RULES TESTED AND VERIFIED SUCCESSFULLY 100%!')
