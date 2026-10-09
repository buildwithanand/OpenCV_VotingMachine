```python
#!/usr/bin/env python3

import time
import RPi.GPIO as GPIO

import FaceSim2
import Sensors


# ============================================================
# GPIO CONFIGURATION
# ============================================================

PINS = {
    "face": 17,
    "finger": 22,
    "temp": 18,
    "bpm": 23,
    "spo2": 24
}

OUTPUT_WINDOW = 2.0
SENSOR_TIMEOUT = 10.0


# ============================================================
# GPIO INITIALIZATION
# ============================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in PINS.values():
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)


# ============================================================
# RESET OUTPUTS
# ============================================================

def reset_outputs():
    for pin in PINS.values():
        GPIO.output(pin, GPIO.LOW)


# ============================================================
# SYNCHRONIZED OUTPUTS
# ============================================================

def trigger_all_outputs(face_ok, finger_ok, sensor_flags):

    print("\n[SYSTEM] Updating all GPIO outputs.")

    pin_states = {
        PINS["face"]: bool(face_ok),
        PINS["finger"]: bool(finger_ok),
        PINS["temp"]: bool(sensor_flags["temp"]),
        PINS["bpm"]: bool(sensor_flags["bpm"]),
        PINS["spo2"]: bool(sensor_flags["spo2"])
    }

    print(
        f"[RESULT] Face={face_ok}, "
        f"Fingerprint={finger_ok}, "
        f"Temperature={sensor_flags['temp']}, "
        f"BPM={sensor_flags['bpm']}, "
        f"SpO2={sensor_flags['spo2']}"
    )

    start = time.monotonic()

    try:
        # Update all outputs consecutively, without delays
        # between individual GPIO writes.
        for pin, state in pin_states.items():
            GPIO.output(
                pin,
                GPIO.HIGH if state else GPIO.LOW
            )

        # Maintain the existing two-second output window.
        remaining = OUTPUT_WINDOW - (time.monotonic() - start)

        if remaining > 0:
            time.sleep(remaining)

    finally:
        reset_outputs()

    print("[SYSTEM] All GPIO outputs LOW.")
    print("[SYSTEM] Ready for the next fingerprint.")


# ============================================================
# MAIN AUTHENTICATION LOOP
# ============================================================

def main_loop():

    print("\n[SYSTEM] Fingerprint-triggered authentication started.")

    while True:

        try:
            # ------------------------------------------------
            # STEP 1: WAIT FOR FINGERPRINT EVENT
            # ------------------------------------------------

            print("\n[SYSTEM] Waiting for a finger...")

            fingerprint = Sensors.wait_for_fingerprint()

            if fingerprint is None:
                continue

            finger_ok = fingerprint["verified"]

            print(
                f"[SYSTEM] Fingerprint result: "
                f"{'MATCH' if finger_ok else 'NO MATCH'}"
            )

            # Do not proceed to face verification if the
            # fingerprint did not match.
            if not finger_ok:
                print("[SYSTEM] Fingerprint rejected.")
                print("[SYSTEM] Waiting for the next attempt.")
                continue

            # ------------------------------------------------
            # STEP 2: FACE CAPTURE / SIMULATION
            # ------------------------------------------------

            print("[SYSTEM] Fingerprint accepted.")
            print("[SYSTEM] Starting face verification.")

            face_ok = FaceSim2.run_once()

            # ------------------------------------------------
            # STEP 3: GET FRESH SENSOR DATA
            # ------------------------------------------------

            print("[SYSTEM] Waiting for fresh sensor readings...")

            sensor_data = Sensors.wait_for_sensor_data(
                after_timestamp=fingerprint["timestamp"],
                timeout=SENSOR_TIMEOUT
            )

            if sensor_data is None:

                print("[WARNING] No fresh sensor data received.")

                sensor_flags = {
                    "temp": False,
                    "bpm": False,
                    "spo2": False
                }

            else:

                sensor_flags = sensor_data["flags"]

                print(
                    f"[SENSORS] BPM={sensor_data['bpm']}, "
                    f"Temperature={sensor_data['temperature']} °C, "
                    f"SpO2={sensor_data['spo2']}%"
                )

            # ------------------------------------------------
            # STEP 4: DISPLAY RESULTS
            # ------------------------------------------------

            print("\n========== VERIFICATION SUMMARY ==========")

            print(
                "Fingerprint:",
                "VERIFIED" if finger_ok else "FAILED"
            )

            print(
                "Face:",
                "VERIFIED" if face_ok else "FAILED"
            )

            if sensor_data is not None:
                print("Sensor flags:", sensor_flags)
            else:
                print("Sensors: NO FRESH DATA")

            print("==========================================")

            # ------------------------------------------------
            # STEP 5: UPDATE ALL OUTPUTS TOGETHER
            # ------------------------------------------------

            trigger_all_outputs(
                face_ok=face_ok,
                finger_ok=finger_ok,
                sensor_flags=sensor_flags
            )

        except KeyboardInterrupt:
            print("\n[SYSTEM] Shutdown requested.")
            break

        except Exception as error:
            print(f"[ERROR] Authentication cycle failed: {error}")

            reset_outputs()
            time.sleep(1)


# ============================================================
# START SYSTEM
# ============================================================

if __name__ == "__main__":

    try:
        print("==========================================")
        print(" DLD BIOMETRIC AUTHENTICATION SYSTEM")
        print(" FINGERPRINT-TRIGGERED FACE SIMULATION")
        print("==========================================")

        # Start the single ESP32 serial listener.
        Sensors.start_listener()

        # Start the authentication sequence.
        main_loop()

    except KeyboardInterrupt:
        print("\n[SYSTEM] Stopping system.")

    finally:
        reset_outputs()
        Sensors.stop_listener()
        GPIO.cleanup()

        print("[SYSTEM] GPIO cleanup complete.")
```
