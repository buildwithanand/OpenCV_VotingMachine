#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import requests
import RPi.GPIO as GPIO

import PicClick
import Sensors


# ============================================================
# CONFIGURATION
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

SERVER_URL = "http://127.0.0.1:5000"
SERVER_START_TIMEOUT = 20.0

SERVER_PROCESS = None


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
    """Set all authentication outputs to LOW."""

    for pin in PINS.values():
        GPIO.output(pin, GPIO.LOW)


# ============================================================
# START FACE-VERIFICATION SERVER
# ============================================================

def start_face_server():
    """
    Start FaceVer.py as a child process and wait until
    its Flask endpoint responds.
    """

    global SERVER_PROCESS

    project_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    server_path = os.path.join(
        project_dir,
        "FaceVer.py"
    )

    if not os.path.isfile(server_path):
        raise FileNotFoundError(
            f"FaceVer.py not found: {server_path}"
        )

    print("\n[SYSTEM] Starting FaceVer.py...")

    # Use the same Python interpreter as Main.py.
    # Run from the project directory so relative database
    # paths resolve to the existing project files.
    SERVER_PROCESS = subprocess.Popen(
        [sys.executable, server_path],
        cwd=project_dir
    )

    deadline = time.monotonic() + SERVER_START_TIMEOUT

    print("[SYSTEM] Waiting for Flask server...")

    while time.monotonic() < deadline:

        if SERVER_PROCESS.poll() is not None:
            raise RuntimeError(
                "FaceVer.py stopped before the Flask server "
                "became available. Check its error output."
            )

        try:
            response = requests.get(
                SERVER_URL + "/",
                timeout=1
            )

            if response.ok:
                print("[SYSTEM] Face-verification server READY.")
                print("[SYSTEM] Existing face database loaded.")
                return

        except requests.RequestException:
            pass

        time.sleep(0.25)

    raise TimeoutError(
        "Face-verification server did not start within "
        f"{SERVER_START_TIMEOUT:.0f} seconds."
    )


# ============================================================
# STOP FACE-VERIFICATION SERVER
# ============================================================

def stop_face_server():

    global SERVER_PROCESS

    if SERVER_PROCESS is None:
        return

    if SERVER_PROCESS.poll() is None:

        print("[SYSTEM] Stopping FaceVer.py...")

        SERVER_PROCESS.terminate()

        try:
            SERVER_PROCESS.wait(timeout=5)

        except subprocess.TimeoutExpired:
            SERVER_PROCESS.kill()
            SERVER_PROCESS.wait()

    SERVER_PROCESS = None


# ============================================================
# SYNCHRONIZED GPIO OUTPUTS
# ============================================================

def trigger_all_outputs(face_ok, finger_ok, sensor_flags):
    """
    Update the five GPIO outputs consecutively without
    intentional delays between individual GPIO writes.

    Keep the output window open for two seconds, then
    reset every output to LOW.
    """

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

        # Update all outputs consecutively.
        for pin, state in pin_states.items():
            GPIO.output(
                pin,
                GPIO.HIGH if state else GPIO.LOW
            )

            print(
                f"[GPIO] BCM {pin}: "
                f"{'HIGH' if state else 'LOW'}"
            )

        # Maintain the two-second output window.
        remaining = OUTPUT_WINDOW - (
            time.monotonic() - start
        )

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

    print("\n[SYSTEM] Authentication system started.")

    while True:

        try:

            # ------------------------------------------------
            # STEP 1: WAIT FOR FINGERPRINT
            # ------------------------------------------------

            print("\n[SYSTEM] Waiting for a fingerprint...")

            fingerprint = Sensors.wait_for_fingerprint()

            if fingerprint is None:
                continue

            finger_ok = bool(
                fingerprint.get("verified", False)
            )

            print(
                "[SYSTEM] Fingerprint result:",
                "VERIFIED" if finger_ok else "FAILED"
            )

            # Do not proceed if the fingerprint failed.
            if not finger_ok:
                print("[SYSTEM] Fingerprint rejected.")
                reset_outputs()
                continue

            # ------------------------------------------------
            # STEP 2: REAL FACE VERIFICATION
            # ------------------------------------------------

            print("[SYSTEM] Fingerprint accepted.")
            print("[SYSTEM] Starting camera capture...")

            # PicClick captures the image and submits it
            # to the FaceVer.py Flask verification server.
            face_ok = bool(PicClick.run_once())

            print(
                "[SYSTEM] Face result:",
                "VERIFIED" if face_ok else "FAILED"
            )

            # Reject the attempt if the face is not verified.
            if not face_ok:
                print("[SYSTEM] Face verification failed.")
                print("[SYSTEM] Authentication rejected.")

                reset_outputs()
                continue

            # ------------------------------------------------
            # STEP 3: WAIT FOR FRESH SENSOR DATA
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
            # STEP 4: VERIFICATION SUMMARY
            # ------------------------------------------------

            print("\n========== VERIFICATION SUMMARY ==========")

            print("Fingerprint: VERIFIED")
            print("Face: VERIFIED")

            if sensor_data is not None:
                print("Sensor flags:", sensor_flags)
            else:
                print("Sensors: NO FRESH DATA")

            print("==========================================")

            # ------------------------------------------------
            # STEP 5: SYNCHRONIZED GPIO OUTPUTS
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

            print(
                f"[ERROR] Authentication cycle failed: {error}"
            )

            reset_outputs()
            time.sleep(1)


# ============================================================
# START AND STOP THE COMPLETE SYSTEM
# ============================================================

if __name__ == "__main__":

    sensor_listener_started = False

    try:

        print("==========================================")
        print(" DLD BIOMETRIC AUTHENTICATION SYSTEM")
        print(" FINGERPRINT + REAL FACE VERIFICATION")
        print(" AUTOMATIC FLASK SERVER STARTUP")
        print("==========================================")

        # STEP 1: Start the face-verification Flask server.
        start_face_server()

        # STEP 2: Start the ESP32 sensor listener.
        Sensors.start_listener()
        sensor_listener_started = True

        # STEP 3: Begin the authentication loop.
        main_loop()

    except KeyboardInterrupt:
        print("\n[SYSTEM] System interrupted.")

    except Exception as error:
        print(f"\n[ERROR] System startup failed: {error}")

    finally:

        # Reset outputs before shutting down.
        try:
            reset_outputs()
        except Exception:
            pass

        # Stop the sensor listener if it was started.
        if sensor_listener_started:
            try:
                Sensors.stop_listener()
            except Exception as error:
                print(
                    f"[WARNING] Sensor shutdown error: {error}"
                )

        # Stop the Flask server started by this program.
        stop_face_server()

        # Release GPIO resources.
        GPIO.cleanup()

        print("[SYSTEM] GPIO cleanup complete.")
        print("[SYSTEM] System shutdown complete.")
      
