import threading
import time
import requests
import RPi.GPIO as GPIO

import FaceVer
import PicClick
import fingerprintverify3
import ExtSensors

# ---------------- GPIO SETUP ----------------

ALL_PINS = [17, 22, 18, 23, 24]

GPIO.setwarnings(False)

if not GPIO.getmode():
    GPIO.setmode(GPIO.BCM)

for pin in ALL_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ---------------- THREADS ----------------

def run_flask():
    print("🌐 Starting Flask server...")
    FaceVer.app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def run_sensors():
    print("❤️ Starting sensor thread...")
    ExtSensors.run_triple_verification()

# ---------------- WAIT FOR FLASK ----------------

def wait_for_flask():
    print("⏳ Waiting for Flask to be ready...")
    while True:
        try:
            r = requests.get("http://127.0.0.1:5000")
            if r.status_code == 200:
                print("✅ Flask is ready")
                break
        except:
            pass
        time.sleep(1)

# ---------------- SENSOR STABILIZATION ----------------

def wait_for_sensor_stabilization():
    print("⏳ Waiting 5 seconds for sensor stabilization...")
    time.sleep(5)

def wait_for_fresh_sensor_data():
    print("⏳ Waiting for fresh sensor data...")

    while True:
        if time.time() - ExtSensors.sensor_last_updated < 1:
            print("✅ Fresh sensor data ready")
            break
        time.sleep(0.2)

# ---------------- GPIO BURST (SELECTIVE) ----------------

def trigger_all_outputs():
    print("⚡ Triggering synchronized output (selective)")

    start_time = time.time()

    # Get results
    face_ok = PicClick.face_result_flag
    finger_ok = fingerprintverify3.fingerprint_result_flag
    sensor_ok = ExtSensors.sensor_flags

    print(f"DEBUG → Face: {face_ok}, Finger: {finger_ok}, Sensors: {sensor_ok}")

    # ---------------- FACE + FINGERPRINT ----------------

    if face_ok:
        GPIO.output(17, GPIO.HIGH)

    if finger_ok:
        GPIO.output(22, GPIO.HIGH)

    # ---------------- SENSORS ----------------
    # DO NOT override sensor GPIO — they already control themselves

    # ---------------- TIMING ----------------

    time.sleep(0.055)  # ≥ 55 ms

    elapsed = time.time() - start_time
    if elapsed < 2:
        time.sleep(2 - elapsed)

    # ---------------- RESET ONLY FACE + FINGERPRINT ----------------

    GPIO.output(17, GPIO.LOW)
    GPIO.output(22, GPIO.LOW)

    print("🔻 Face & Fingerprint outputs reset (sensors untouched)")

# ---------------- MAIN LOOP ----------------

def main_loop():
    print("🚀 MAIN LOOP STARTED")

    wait_for_flask()

    while True:
        print("\n👆 Waiting for fingerprint trigger...")

        # Step 1: Fingerprint (trigger)
        print("👉 Calling Fingerprint")
        fingerprintverify3.run_once()
        print("✅ Fingerprint done")

        # Step 2: Face verification
        print("📸 Running Face Verification...")
        PicClick.run_once()
        print("✅ Face done")

        # Step 3: Wait for sensor stabilization
        wait_for_sensor_stabilization()

        # Step 4: Ensure fresh sensor data
        wait_for_fresh_sensor_data()

        # Step 5: Final synchronized output
        trigger_all_outputs()

        print("🔁 Back to idle...\n")

# ---------------- START SYSTEM ----------------

t1 = threading.Thread(target=run_flask)
t2 = threading.Thread(target=run_sensors)
t3 = threading.Thread(target=main_loop)

t1.start()
t2.start()
t3.start()

t1.join()
t2.join()
t3.join()
