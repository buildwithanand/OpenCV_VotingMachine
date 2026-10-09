```python
#!/usr/bin/env python3

import serial
import time
import json

# ---------------- SERIAL CONFIGURATION ----------------

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

# ---------------- VERIFICATION RESULTS ----------------

verification_results = {
    "fingerprint": {
        "verified": False,
        "user_id": None
    },
    "sensors": {
        "received": False,
        "bpm": None,
        "temperature": None,
        "spo2": None
    }
}


def reset_results():
    """Reset stored results before a new verification attempt."""

    verification_results["fingerprint"]["verified"] = False
    verification_results["fingerprint"]["user_id"] = None

    verification_results["sensors"]["received"] = False
    verification_results["sensors"]["bpm"] = None
    verification_results["sensors"]["temperature"] = None
    verification_results["sensors"]["spo2"] = None


def print_results():
    """Display collected verification results."""

    print("\n" + "=" * 45)
    print("       VERIFICATION RESULTS")
    print("=" * 45)

    fingerprint = verification_results["fingerprint"]
    sensors = verification_results["sensors"]

    print("\nFINGERPRINT")
    print("-" * 25)

    if fingerprint["verified"]:
        print("Status   : VERIFIED")
        print(f"User ID  : {fingerprint['user_id']}")
    else:
        print("Status   : NOT VERIFIED")

    print("\nHEALTH SENSOR READINGS")
    print("-" * 25)

    if sensors["received"]:
        print(f"BPM         : {sensors['bpm']}")
        print(f"Temperature : {sensors['temperature']} °C")
        print(f"SpO2        : {sensors['spo2']} %")
    else:
        print("Status      : NO VALID SENSOR DATA RECEIVED")

    print("\n" + "=" * 45)


def export_results():
    """
    Export collected results as JSON.
    The main program can load this file later.
    """

    filename = "verification_results.json"

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(verification_results, file, indent=4)

    print(f"\nResults saved to: {filename}")


def main():

    print("Fingerprint and Sensor Verification Module")
    print("Waiting for ESP32 data...\n")

    try:
        with serial.Serial(
            SERIAL_PORT,
            BAUD_RATE,
            timeout=1
        ) as ser:

            time.sleep(2)
            ser.reset_input_buffer()

            while True:

                if ser.in_waiting == 0:
                    time.sleep(0.05)
                    continue

                line = ser.readline().decode(
                    "utf-8",
                    errors="ignore"
                ).strip()

                if not line:
                    continue

                print(f"[ESP32] {line}")

                # -------- FINGERPRINT MATCH --------

                if line.startswith("V:MATCH:"):

                    user_id = line.split(":")[-1]

                    verification_results["fingerprint"][
                        "verified"
                    ] = True

                    verification_results["fingerprint"][
                        "user_id"
                    ] = user_id

                    print(f"Fingerprint verified: User {user_id}")

                # -------- FINGERPRINT FAILURE --------

                elif line == "V:NOMATCH" or line.startswith("V:NOMATCH:"):

                    verification_results["fingerprint"][
                        "verified"
                    ] = False

                    verification_results["fingerprint"][
                        "user_id"
                    ] = None

                    print("Fingerprint verification failed.")

                # -------- HEALTH SENSOR DATA --------

                elif line.startswith("H:"):

                    try:
                        data = line[2:].split(",")

                        if len(data) != 3:
                            print("Invalid sensor data format.")
                            continue

                        bpm = int(data[0])
                        temperature = float(data[1])
                        spo2 = int(data[2])

                        # Basic plausibility checks.
                        # These do not establish that a person is healthy.
                        if not (0 <= bpm <= 300):
                            print("Invalid BPM reading.")
                            continue

                        if not (-50 <= temperature <= 100):
                            print("Invalid temperature reading.")
                            continue

                        if not (0 <= spo2 <= 100):
                            print("Invalid SpO2 reading.")
                            continue

                        verification_results["sensors"][
                            "received"
                        ] = True

                        verification_results["sensors"][
                            "bpm"
                        ] = bpm

                        verification_results["sensors"][
                            "temperature"
                        ] = temperature

                        verification_results["sensors"][
                            "spo2"
                        ] = spo2

                        print("Sensor readings collected successfully.")

                    except (ValueError, IndexError) as error:
                        print(f"Could not parse sensor data: {error}")

                # -------- ESP32 STATUS MESSAGES --------

                elif line.startswith("MSG:"):

                    print(f"System message: {line[4:]}")

                # -------- OPTIONAL VERIFICATION SUMMARY --------

                elif line == "SHOW_RESULTS":

                    print_results()
                    export_results()

    except serial.SerialException as error:
        print(f"Serial connection error: {error}")

    except KeyboardInterrupt:
        print("\nVerification module stopped.")

    finally:
        print("Verification module closed.")


if __name__ == "__main__":
    main()
```
