from flask import Blueprint, request, jsonify
import requests
import os
import base64
from utils import get_timestamp, get_password, format_phone_number
import os
from datetime import datetime
import threading
import time
from flask import Flask
import threading

payment_status_store = {}
payment_status_lock = threading.Lock()

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
        res_data = res.json()

        checkout_request_id = res_data["CheckoutRequestID"]

        with payment_status_lock:
            payment_status_store[checkout_request_id] = None

        def delayed_query():
            time.sleep(20)
            with payment_status_lock:
                if payment_status_store[checkout_request_id] is None:
                    print("No callback, querying manually...")
                    try:
                        status_result = query_transaction_status(checkout_request_id, access_token, get_timestamp())
                        payment_status_store[checkout_request_id] = status_result
                    except Exception as e:
                        payment_status_store[checkout_request_id] = {"error": str(e)}

        threading.Thread(target=delayed_query).start()

        waited = 0
        while waited < 20:
            time.sleep(1)
            with payment_status_lock:
                result = payment_status_store.get(checkout_request_id)
                if result:
                    del payment_status_store[checkout_request_id]
                    return jsonify({"success": True, "result": result})
            waited += 1

        # Timeout
        return jsonify({"success": False, "message": "Timeout waiting for payment status"}), 504

    except Exception as e:
        return jsonify({"success": False, "message": "Failed to initiate STK Push", "error": str(e)}), 500


@bp.route("/callback", methods=["POST"])
def stk_callback():
    callback_data = request.json.get("Body", {}).get("stkCallback", {})
    print("Callback received:", callback_data)

    checkout_id = callback_data.get("CheckoutRequestID")

    with payment_status_lock:
        payment_status_store[checkout_id] = callback_data

    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


def query_transaction_status(checkout_request_id, access_token, timestamp):
    short_code = os.getenv("BUSINESS_SHORT_CODE")
    password = get_password(timestamp)

    payload = {
        "BusinessShortCode": short_code,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query", json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
