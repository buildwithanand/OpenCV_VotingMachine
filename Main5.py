import threading
import time
import RPi.GPIO as GPIO

import Facesim2
import FingerPrintVer
import ExtSensor


# ==========================================
# GPIO CONFIGURATION
# ==========================================

PINS = {
    "face": 17,
    "finger": 22,
    "temp": 18,
    "bpm": 23,
    "spo2": 24
}

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in PINS.values():
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


# ==========================================
# SENSOR THREAD
# ==========================================

def run_sensors():
    print("[SYSTEM] Starting sensor thread...")
    ExtSensor.run_triple_verification()


# ==========================================
# WAIT FOR SENSOR STABILIZATION
# ==========================================

def wait_for_sensor_stabilization():
    print("[SYSTEM] Waiting 5 seconds for sensors...")
    time.sleep(5)


def wait_for_fresh_sensor_data():
    print("[SYSTEM] Waiting for fresh sensor data...")

    while True:
        if time.time() - ExtSensor.sensor_last_updated < 1:
            print("[SYSTEM] Fresh sensor data ready.")
            break

        time.sleep(0.2)


# ==========================================
# SYNCHRONIZED OUTPUTS
# ==========================================

def trigger_all_outputs():
    print("\n[SYSTEM] Triggering synchronized outputs.")

    start_time = time.time()

    # Get the latest results from each module
    face_ok = Facesim2.face_result_flag
    finger_ok = FingerPrintVer.fingerprint_result_flag
    sensor_ok = ExtSensor.sensor_flags

    print(
        f"[DEBUG] Face: {face_ok}, "
        f"Fingerprint: {finger_ok}, "
        f"Sensors: {sensor_ok}"
    )

    # Map each verification result to its GPIO
    pin_states = {
        PINS["face"]: face_ok,
        PINS["finger"]: finger_ok,
        PINS["temp"]: sensor_ok["temp"],
        PINS["bpm"]: sensor_ok["bpm"],
        PINS["spo2"]: sensor_ok["spo2"]
    }

    # Update all outputs together
    for pin, state in pin_states.items():
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

    # Keep the output pulse at least 55 ms
    time.sleep(0.055)

    # Maintain the original 2-second output window
    elapsed = time.time() - start_time

    if elapsed < 2:
        time.sleep(2 - elapsed)

    # Reset all outputs
    for pin in pin_states:
        GPIO.output(pin, GPIO.LOW)

    print("[SYSTEM] All outputs reset.")


# ==========================================
# MAIN AUTHENTICATION LOOP
# ==========================================

def main_loop():
    print("\n[SYSTEM] MAIN LOOP STARTED")

    wait_for_sensor_stabilization()

    while True:
        try:
            print("\n[SYSTEM] Waiting for fingerprint trigger...")

            # Step 1: Fingerprint verification
            print("[SYSTEM] Calling fingerprint verification...")
            FingerPrintVer.run_once()
            print("[SYSTEM] Fingerprint check completed.")

            # Step 2: Simulated face verification
            print("[SYSTEM] Running simulated face verification...")
            Facesim2.run_once()
            print("[SYSTEM] Face simulation completed.")

            # Step 3: Allow sensors to stabilize
            wait_for_sensor_stabilization()

            # Step 4: Wait for fresh sensor measurements
            wait_for_fresh_sensor_data()

            # Step 5: Trigger the synchronized GPIO outputs
            trigger_all_outputs()

            print("[SYSTEM] Returning to idle...\n")

        except KeyboardInterrupt:
            print("\n[SYSTEM] Shutdown requested.")
            break

        except Exception as error:
            print(f"[ERROR] Authentication cycle failed: {error}")
            time.sleep(1)


# ==========================================
# START SYSTEM
# ==========================================

if __name__ == "__main__":
    try:
        print("====================================")
        print(" DLD BIOMETRIC AUTHENTICATION SYSTEM")
        print(" CAMERA-FREE FACE SIMULATION ENABLED")
        print("====================================")

        # Start sensor monitoring in the background
        sensor_thread = threading.Thread(
            target=run_sensors,
            daemon=True
        )
        sensor_thread.start()

        # Start the authentication loop
        main_loop()

    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopping system...")

    finally:
        GPIO.cleanup()
        print("[SYSTEM] GPIO cleanup complete.")
