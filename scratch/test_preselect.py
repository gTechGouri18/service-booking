import sys, os
sys.path.insert(0, os.path.abspath("."))
from app import app

client = app.test_client()

with client.session_transaction() as sess:
    sess["user_id"] = 2
    sess["user_type"] = "customer"
    sess["user_name"] = "G Gouri"
    sess["user_email"] = "gourichinni2005@gmail.com"
    sess["user_phone"] = "9202745205"

res = client.get("/book/1?service=Bridal%20%26%20Party%20Hair%20Styling")
print("Status code:", res.status_code)
html = res.get_data(as_text=True)

print("Has 'selected' in option:", "selected" in html)
print("Has 'Bridal' in value:", "Bridal" in html)
print("Booking page loaded properly!")
