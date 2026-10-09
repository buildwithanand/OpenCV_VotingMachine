# ============================================================
# FaceSim2.py
# Camera-Free Face Verification Simulator
# DLD Biometric Authentication Project
# ============================================================

import random
import time


# ============================================================
# FACE VERIFICATION RESULT
# ============================================================

face_result_flag = False


# ============================================================
# RUN ONE FACE VERIFICATION
# ============================================================

def run_once():

    global face_result_flag

    print("\n========================================")
    print("       FACE VERIFICATION SIMULATOR")
    print("========================================")

    print("[FACE] Processing face verification...")

    time.sleep(1)

    # Simulated result.
    # Replace with actual face recognition when ready.
    face_result_flag = random.choice([True, False])

    if face_result_flag:

        print("[FACE] Face verified successfully!")
        print("[FACE] Status: VERIFIED")

    else:

        print("[FACE] Face verification failed!")
        print("[FACE] Status: NOT VERIFIED")

    print("========================================\n")

    return face_result_flag


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    print("Starting Face Verification Simulator.")
    print("Press CTRL+C to stop.\n")

    try:

        while True:

            run_once()
            time.sleep(2)

    except KeyboardInterrupt:

        print("\n[FACE] Simulator stopped.")
