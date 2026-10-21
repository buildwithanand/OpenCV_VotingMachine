#!/usr/bin/env python3

import os
import time
import subprocess
import requests
import RPi.GPIO as GPIO


# ============================================================
# CONFIGURATION
# ============================================================

IMAGE_PATH = os.path.abspath("temp.jpg")

VERIFY_URL = "http://127.0.0.1:5000/verify"

CAMERA_TIMEOUT_MS = 2000

REQUEST_TIMEOUT = 20

OUTPUT_PIN = 17


# ============================================================
# GPIO CONFIGURATION
# ============================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(OUTPUT_PIN, GPIO.OUT, initial=GPIO.LOW)


# ============================================================
# VERIFICATION RESULT
# ============================================================

face_result_flag = False


# ============================================================
# CAPTURE IMAGE
# ============================================================

def capture_image():

    print("\n[CAMERA] Capturing image...")

    # Remove an old image so we cannot accidentally reuse it.
    if os.path.exists(IMAGE_PATH):
        os.remove(IMAGE_PATH)

    command = [
        "rpicam-still",
        "-n",
        "--output", IMAGE_PATH,
        "--timeout", str(CAMERA_TIMEOUT_MS)
    ]

    try:

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15
        )

        if process.returncode != 0:

            print("[CAMERA ERROR] Capture failed.")

            if process.stderr:
                print(process.stderr)

            return False

        if not os.path.isfile(IMAGE_PATH):

            print("[CAMERA ERROR] Image file was not created.")

            return False

        if os.path.getsize(IMAGE_PATH) == 0:

            print("[CAMERA ERROR] Captured image is empty.")

            return False

        print("[CAMERA] Image captured successfully.")

        print(
            f"[CAMERA] File size: "
            f"{os.path.getsize(IMAGE_PATH)} bytes"
        )

        return True

    except subprocess.TimeoutExpired:

        print("[CAMERA ERROR] Capture timed out.")

        return False

    except Exception as error:

        print(f"[CAMERA ERROR] {error}")

        return False


# ============================================================
# VERIFY IMAGE USING EXISTING FLASK SERVER
# ============================================================

def verify_image():

    global face_result_flag

    print("[FACE] Sending image to Flask server...")

    try:

        # The context manager ensures the image file is closed.
        with open(IMAGE_PATH, "rb") as image_file:

            response = requests.post(
                VERIFY_URL,
                files={
                    "image": (
                        "temp.jpg",
                        image_file,
                        "image/jpeg"
                    )
                },
                timeout=REQUEST_TIMEOUT
            )

        print("[SERVER] HTTP status:", response.status_code)

        response.raise_for_status()

        result = response.json()

        print("[SERVER] Response:", result)

        # ----------------------------------------------------
        # CASE 1: SERVER REPORTS NO FACE
        # ----------------------------------------------------

        if result.get("status") == "No Face Detected":

            print("[FACE] No face detected by the server.")

            face_result_flag = False

            return False

        # ----------------------------------------------------
        # CASE 2: SERVER REPORTS AN ERROR
        # ----------------------------------------------------

        if "error" in result:

            print("[SERVER ERROR]", result["error"])

            face_result_flag = False

            return False

        # ----------------------------------------------------
        # CASE 3: FACE DETECTED AND IDENTITY CHECKED
        # ----------------------------------------------------

        results = result.get("results", [])

        if not results:

            print("[FACE] No verification results returned.")

            face_result_flag = False

            return False

        for item in results:

            status = item.get("status", "UNKNOWN")

            print("[FACE] Recognition status:", status)

            if status == "VERIFIED":

                print("[FACE] Identity verified.")

                print("[FACE] Name:", item.get("name", "Unknown"))

                print(
                    "[FACE] Confidence:",
                    item.get("confidence", "N/A")
                )

                face_result_flag = True

                return True

        # A face may have been detected but not recognised.
        print("[FACE] No enrolled identity matched.")

        face_result_flag = False

        return False

    except requests.exceptions.ConnectionError:

        print(
            "[SERVER ERROR] Cannot connect to Flask. "
            "Check that FaceVer.py is running on port 5000."
        )

        face_result_flag = False

        return False

    except requests.exceptions.Timeout:

        print("[SERVER ERROR] Verification request timed out.")

        face_result_flag = False

        return False

    except requests.exceptions.RequestException as error:

        print("[SERVER ERROR]", error)

        face_result_flag = False

        return False

    except ValueError as error:

        print("[SERVER ERROR] Invalid JSON response:", error)

        face_result_flag = False

        return False

    except Exception as error:

        print("[ERROR]", error)

        face_result_flag = False

        return False


# ============================================================
# MAIN FACE VERIFICATION FUNCTION
# ============================================================

def run_once():

    global face_result_flag

    face_result_flag = False

    GPIO.output(OUTPUT_PIN, GPIO.LOW)

    print("\n========================================")
    print("       FACE VERIFICATION SYSTEM")
    print("========================================")

    try:

        # STEP 1: Capture a fresh image.
        if not capture_image():

            return False

        # STEP 2: Submit the image to the existing server.
        verified = verify_image()

        # STEP 3: Update GPIO according to the result.
        if verified:

            GPIO.output(OUTPUT_PIN, GPIO.HIGH)

            print("[GPIO] GPIO 17 HIGH")

        else:

            GPIO.output(OUTPUT_PIN, GPIO.LOW)

            print("[GPIO] GPIO 17 LOW")

        return verified

    finally:

        print("[FACE] Verification cycle completed.")


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    try:

        print("[SYSTEM] Face verification started.")

        while True:

            run_once()

            # Preserve the original two-second delay.
            time.sleep(2)

    except KeyboardInterrupt:

        print("\n[SYSTEM] Program stopped.")

    finally:

        GPIO.output(OUTPUT_PIN, GPIO.LOW)

        GPIO.cleanup()

        print("[SYSTEM] GPIO cleanup complete.")
