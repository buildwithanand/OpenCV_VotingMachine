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
MINIMUM_PULSE = 0.055
SENSOR_TIMEOUT = 10


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in PINS.values():

    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


# ============================================================
# GPIO RESET
# ============================================================

def reset_all_outputs():

    for pin in PINS.values():
        GPIO.output(pin, GPIO.LOW)


# ============================================================
# SYNCHRONIZED GPIO OUTPUTS
# ============================================================

def trigger_all_outputs(face_ok, finger_ok, sensor_flags):

    print("\n[SYSTEM] Triggering synchronized outputs.")

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

    start_time = time.monotonic()

    try:

        # Apply each output state in sequence.
        # All GPIO writes occur within a very short interval,
        # rather than using separate delays for each signal.
        for pin, state in pin_states.items():

            GPIO.output(
                pin,
                GPIO.HIGH if state else GPIO.LOW
            )

        # Maintain the original output window.
        # The 2-second window exceeds the required 55 ms pulse.
        elapsed = time.monotonic() - start_time

        remaining = max(
            MINIMUM_PULSE,
            OUTPUT_WINDOW - elapsed
        )

        time.sleep(remaining)

    finally:

        reset_all_outputs()

    print("[SYSTEM] All outputs reset.")


# ============================================================
# DISPLAY CURRENT VERIFICATION RESULTS
# ============================================================

def display_results(fingerprint, face_ok, sensor_data):

    print("\n" + "=" * 50)
    print("       BIOMETRIC VERIFICATION RESULTS")
    print("=" * 50)

    print(
        "Fingerprint:",
        "VERIFIED" if fingerprint["verified"]
        else "NOT VERIFIED"
    )

    if fingerprint["user_id"] is not None:
        print("User ID:", fingerprint["user_id"])

    print(
        "Face:",
        "VERIFIED" if face_ok
        else "NOT VERIFIED"
    )

    if sensor_data is None:

        print("Sensors: NO FRESH DATA RECEIVED")

    else:

        print("BPM:", sensor_data["bpm"])
        print("Temperature:", sensor_data["temperature"], "°C")
        print("SpO2:", sensor_data["spo2"], "%")

        print("Sensor output flags:", sensor_data["flags"])

    print("=" * 50)


# ============================================================
# MAIN AUTHENTICATION LOOP
# ============================================================

def main_loop():

    print("\n[SYSTEM] MAIN LOOP STARTED.")

    while True:

        try:

            # ------------------------------------------------
            # STEP 1: WAIT FOR FINGERPRINT EVENT
            # ------------------------------------------------

            print("\n[SYSTEM] Waiting for fingerprint verification...")

            fingerprint = Sensors.wait_for_fingerprint()

            if fingerprint is None:
                continue

            print(
                "[SYSTEM] Fingerprint event received:",
                fingerprint["verified"]
            )

            # ------------------------------------------------
            # STEP 2: RUN FACE VERIFICATION
            # ------------------------------------------------

            print("[SYSTEM] Running face verification...")

            face_ok = FaceSim2.run_once()

            # ------------------------------------------------
            # STEP 3: WAIT FOR FRESH SENSOR DATA
            # ------------------------------------------------

            print("[SYSTEM] Waiting for fresh sensor readings...")

            sensor_data = Sensors.wait_for_sensor_data(
                after_timestamp=fingerprint["timestamp"],
                timeout=SENSOR_TIMEOUT
            )

            # ------------------------------------------------
            # STEP 4: DETERMINE SENSOR OUTPUT FLAGS
            # ------------------------------------------------

            if sensor_data is None:

                print("[WARNING] No fresh sensor data received.")

                sensor_flags = {
                    "temp": False,
                    "bpm": False,
                    "spo2": False
                }

            else:

                sensor_flags = sensor_data["flags"]

            # ------------------------------------------------
            # STEP 5: DISPLAY RESULTS
            # ------------------------------------------------

            display_results(
                fingerprint,
                face_ok,
                sensor_data
            )

            # ------------------------------------------------
            # STEP 6: SYNCHRONIZED GPIO OUTPUTS
            # ------------------------------------------------

            trigger_all_outputs(
                face_ok=face_ok,
                finger_ok=fingerprint["verified"],
                sensor_flags=sensor_flags
            )

            # ------------------------------------------------
            # STEP 7: RETURN TO IDLE
            # ------------------------------------------------

            print("[SYSTEM] Returning to idle.")

        except KeyboardInterrupt:

            print("\n[SYSTEM] Shutdown requested.")
            break

        except Exception as error:

            print(f"[ERROR] Authentication cycle failed: {error}")

            reset_all_outputs()

            time.sleep(1)


# ============================================================
# START SYSTEM
# ============================================================

if __name__ == "__main__":

    try:

        print("========================================")
        print(" DLD BIOMETRIC AUTHENTICATION SYSTEM")
        print(" CAMERA-FREE FACE SIMULATION ENABLED")
        print("========================================")

        # Start exactly one ESP32 serial listener.
        Sensors.start_listener()

        # Start the authentication controller.
        main_loop()

    except KeyboardInterrupt:

        print("\n[SYSTEM] Stopping system.")

    finally:

        reset_all_outputs()

        Sensors.stop_listener()

        GPIO.cleanup()

        print("[SYSTEM] GPIO cleanup complete.")
