from flask import Blueprint, request, jsonify
import requests
import os
import base64
from utils import get_timestamp, get_password, format_phone_number
import os

status_bp = Blueprint('transaction_status', __name__)

bp = Blueprint('mpesa', __name__)

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    auth = f"{consumer_key}:{consumer_secret}"
    encoded_auth = base64.b64encode(auth.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("access_token")

@bp.route("/stk-push", methods=["POST"])
def stk_push():
    try:
        data = request.json
        phone = data.get("phoneNumber")
        amount = data.get("amount")

        if not phone or not amount:
            return jsonify({"error": "Phone number and amount are required"}), 400

        formatted_phone = format_phone_number(phone)
        access_token = get_access_token()

        timestamp = get_timestamp()
        password = get_password(timestamp)
        short_code = os.getenv("BUSINESS_SHORT_CODE")
        callback_url = os.getenv("CALLBACK_URL")

        payload = {
            "BusinessShortCode": short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": formatted_phone,
            "PartyB": short_code,
            "PhoneNumber": formatted_phone,
            "CallBackURL": callback_url,
            "AccountReference": "Test Payment",
            "TransactionDesc": "Test Payment"
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        res = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
        res.raise_for_status()

        return jsonify({"success": True, "message": "STK Push initiated successfully", "data": res.json()})

    except Exception as e:
        return jsonify({"success": False, "message": "Failed to initiate STK Push", "error": str(e)}), 500

@bp.route("/callback", methods=["POST"])
def stk_callback():
    callback_data = request.json.get("Body", {}).get("stkCallback", {})
    print("Callback received:", callback_data)

    if callback_data.get("ResultCode") == 0:
        print("Payment Successful:", callback_data.get("CallbackMetadata", {}).get("Item"))
    else:
        print("Payment Failed:", callback_data.get("ResultDesc"))

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})

