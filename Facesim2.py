# ============================================================
# FaceSim.py
# Camera-Free Face Verification Simulator
# DLD Biometric Authentication Project
# ============================================================

import random
import time

# Stores the result of the latest verification attempt
face_result_flag = False


def run_once():
    """
    Simulates one face verification attempt.

    Returns:
        True  -> Face verified
        False -> Face not verified
    """

    global face_result_flag

    print("\n========================================")
    print("       FACE VERIFICATION SIMULATOR")
    print("========================================")

    # Simulate the time required for face verification
    print("[FACE] Processing face verification...")
    time.sleep(1)

    # Randomly generate the verification result
    face_result_flag = random.choice([True, False])

    if face_result_flag:
        print("[FACE] Face verified successfully!")
        print("[FACE] Status: VERIFIED")
    else:
        print("[FACE] Face verification failed!")
        print("[FACE] Status: NOT VERIFIED")

    print("========================================\n")

    return face_result_flag


# Allows the simulator to be tested independently
if _name_ == "_main_":

    print("Starting Face Verification Simulator")
    print("Press CTRL+C to stop.\n")

    try:
        while True:
            run_once()
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[FACE] Simulator stopped.")
