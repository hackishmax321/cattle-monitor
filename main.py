from fastapi import FastAPI
import firebase_admin
from firebase_admin import credentials, db
from firestore_db import get_firestore_client
import asyncio
import traceback
import requests  # Import requests for making API calls
from datetime import datetime

# Initialize Firebase Admin SDK
cred = credentials.Certificate("cattleproject-fbb10-firebase-adminsdk-kvejw-febb71530d.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://cattleproject-fbb10-default-rtdb.firebaseio.com/"
})

# Firestore Database Client
db_firestore = get_firestore_client()

app = FastAPI()

# Global dictionary to store logged data
iot_data = {"BPM": None, "DegreeC": None, "Spo2": None}

# Define threshold values
THRESHOLDS = {
    "BPM": {"min": 95, "max": 100},  # Example BPM range
    "DegreeC": {"min": 38.5, "max": 39.5},  # Example body temperature range
    "Spo2": {"min": 48, "max": 84}  # Example SpO2 range
}

SMS_API_URL = "https://app.notify.lk/api/v1/send"
USER_ID = "29106"
API_KEY = "dOrAUpqYTxOQJBtQjcsN"
SENDER_ID = "NotifyDEMO"
MOBILE_NUMBER = "0725237603" 

async def log_realtime_data():
    """Continuously logs data every 1 minute from Firebase Realtime Database."""
    while True:
        try:
            # Fetch latest data from Firebase Realtime Database
            iot_data["BPM"] = db.reference('BPM').get()
            iot_data["DegreeC"] = db.reference('DegreeC').get()
            iot_data["Spo2"] = db.reference('Spo2').get()

            print(f"Logged Data: {iot_data}")

            # Check for exceeded thresholds and create notifications
            await check_thresholds_and_notify(iot_data)

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"Error fetching data:\n{error_trace}")

        await asyncio.sleep(60)  

async def check_thresholds_and_notify(data):
    """Check if IoT data exceeds defined thresholds and create Firestore notification + send SMS."""
    try:
        notifications = []
        current_date = datetime.now().strftime("%Y-%m-%d")

        for key, value in data.items():
            if value is not None:
                min_val, max_val = THRESHOLDS[key]["min"], THRESHOLDS[key]["max"]

                if value < min_val or value > max_val:
                    message = f"{key} Alert! {key} value {value} is out of range ({min_val}-{max_val})."

                    notification = {
                        "user": None,  
                        "sender": "System",
                        "title": f"{key} Alert!",
                        "message": message,
                        "date": current_date,
                        "reference_values": data
                    }
                    notifications.append(notification)

                    # Send SMS Alert
                    # send_sms_alert(MOBILE_NUMBER, message)

        # Store notifications in Firestore
        if notifications:
            for notification in notifications:
                try:
                    db_firestore.collection("new_notifications").add(notification)
                    print(f"Notification saved in 'new_notifications': {notification}")
                except Exception as e:
                    error_trace = traceback.format_exc()
                    print(f"Error saving notification:\n{error_trace}")

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in check_thresholds_and_notify:\n{error_trace}")

def send_sms_alert(mobile, message):
    """Send an SMS notification using notify.lk API."""
    try:
        formatted_mobile = "94" + mobile[1:]  
        response = requests.get(SMS_API_URL, params={
            "user_id": USER_ID,
            "api_key": API_KEY,
            "sender_id": SENDER_ID,
            "to": formatted_mobile,
            "message": message
        })
        print(f"SMS sent to {formatted_mobile}: {response.json()}")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error sending SMS:\n{error_trace}")

@app.on_event("startup")
async def startup_event():
    """Starts logging data when the FastAPI app starts."""
    asyncio.create_task(log_realtime_data())

@app.get("/")
def read_root():
    return {"message": "FastAPI with Firebase Realtime Database is running"}

@app.get("/latest-iot-data")
def get_latest_iot_data():
    """Returns the latest logged IoT data."""
    return iot_data
