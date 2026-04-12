import threading
import time
import RPi.GPIO as GPIO

import FaceVer
import PicClick
import fingerprintverify3
import ExtSensors

# ---------------- GPIO SETUP ----------------

ALL_PINS = [17, 22, 18, 23, 24]

GPIO.setmode(GPIO.BCM)
for pin in ALL_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# ---------------- THREADS ----------------

def run_flask():
    FaceVer.app.run(host="0.0.0.0", port=5000, debug=False)

def run_sensors():
    ExtSensors.run_triple_verification()

# ---------------- GPIO BURST ----------------

def trigger_all_outputs():
    print("⚡ Triggering synchronized output")

    start_time = time.time()

    for pin in ALL_PINS:
        GPIO.output(pin, GPIO.HIGH)

    time.sleep(0.055)  # ≥ 55 ms

    elapsed = time.time() - start_time
    if elapsed < 2:
        time.sleep(2 - elapsed)

    for pin in ALL_PINS:
        GPIO.output(pin, GPIO.LOW)

    print("🔻 Outputs reset")

# ---------------- MAIN LOOP ----------------

def main_loop():
    time.sleep(3)  # wait for Flask

    while True:
        print("\n👆 Waiting for fingerprint trigger...")

        # Step 1: Fingerprint (TRIGGER)
        fingerprintverify3.run_once()

        print("📸 Running Face Verification...")
        PicClick.run_once()

        print("❤️ Sensors already running...")

        # Step 2: Final synchronized output
        trigger_all_outputs()

        print("🔁 Back to idle...\n")

# ---------------- START ----------------

t1 = threading.Thread(target=run_flask)
t2 = threading.Thread(target=run_sensors)
t3 = threading.Thread(target=main_loop)

t1.start()
t2.start()
t3.start()

t1.join()
t2.join()
t3.join()
