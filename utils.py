import base64
import os
from datetime import datetime

def get_timestamp():
    return datetime.now().strftime('%Y%m%d%H%M%S')

def get_password(timestamp):
    short_code = os.getenv("BUSINESS_SHORT_CODE")
    passkey = os.getenv("PASS_KEY")
    data_to_encode = f"{short_code}{passkey}{timestamp}"
    encoded = base64.b64encode(data_to_encode.encode()).decode()
    return encoded

def format_phone_number(phone):
    if phone.startswith("0"):
        return "254" + phone[1:]
    elif phone.startswith("+254"):
        return phone[1:]
    return phone
