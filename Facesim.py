# FaceSim.py
# Camera-free face verification simulator for DLD
# TESTING ONLY - does not perform actual face recognition

face_result_flag = False


def run_once():
    """
    Simulates one face-verification attempt.
    Returns True if verified, False otherwise.
    """

    global face_result_flag

    print("\n========== FACE VERIFICATION SIMULATOR ==========")
    print("1. Simulate FACE VERIFIED")
    print("2. Simulate FACE NOT VERIFIED")
    print("0. Exit simulator")
    print("=================================================")

    while True:
        choice = input("Enter your choice (1/2/0): ").strip()

        if choice == "1":
            face_result_flag = True
            print("\n[FACE] Face verified successfully!")
            print("[FACE] Result: VERIFIED")
            return True

        elif choice == "2":
            face_result_flag = False
            print("\n[FACE] Face verification failed!")
            print("[FACE] Result: NOT VERIFIED")
            return False

        elif choice == "0":
            face_result_flag = False
            print("\n[FACE] Verification cancelled.")
            return False

        else:
            print("Invalid choice. Enter 1, 2, or 0.")
