import threading
import time
import requests
import RPi.GPIO as GPIO

import FaceVer
import PicClick
import FingerPrintVer
import ExtSensor

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

# ---------------- GPIO BURST (SELECTIVE) ----------------

def trigger_all_outputs():
    print("⚡ Triggering synchronized output (selective)")

    start_time = time.time()

    # Collect results from modules
    face_ok = PicClick.face_result_flag
    finger_ok = fingerprintverify3.fingerprint_result_flag
    sensor_ok = ExtSensors.sensor_flags

    print(f"DEBUG → Face: {face_ok}, Finger: {finger_ok}, Sensors: {sensor_ok}")

    # Map pins to results
    pin_states = {
        17: face_ok,                     # Face
        22: finger_ok,                   # Fingerprint
        18: sensor_ok["temp"],           # Temp
        23: sensor_ok["bpm"],            # BPM
        24: sensor_ok["spo2"]            # SpO2
    }

    # Set only valid pins HIGH
    for pin, state in pin_states.items():
        if state:
            GPIO.output(pin, GPIO.HIGH)

    # Hold ≥ 55 ms
    time.sleep(0.055)

    # Ensure total ≤ 2 sec window
    elapsed = time.time() - start_time
    if elapsed < 2:
        time.sleep(2 - elapsed)

    # Reset all pins
    for pin in pin_states.keys():
        GPIO.output(pin, GPIO.LOW)

    print("🔻 Outputs reset")

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

        # Step 3: Sensors already running in background
        print("❤️ Using latest sensor values")

        # Step 4: Final synchronized output
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
