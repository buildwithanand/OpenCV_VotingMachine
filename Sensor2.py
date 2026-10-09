#!/usr/bin/env python3

import serial
import time
import threading
import queue


# ============================================================
# SERIAL CONFIGURATION
# ============================================================

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200


# ============================================================
# SENSOR ACCEPTANCE THRESHOLDS
# ============================================================

TEMP_MIN = 15.0
TEMP_MAX = 45.0

BPM_MIN = 28
BPM_MAX = 200

SPO2_MIN = 75
SPO2_MAX = 100


# ============================================================
# EVENT QUEUES
# ============================================================

fingerprint_events = queue.Queue()
sensor_events = queue.Queue()

stop_event = threading.Event()

listener_thread = None
listener_error = None


# ============================================================
# SENSOR VALIDATION
# ============================================================

def validate_sensor_data(bpm, temperature, spo2):
    """
    Reject obviously implausible readings.

    Passing these checks does not establish medical health.
    """

    if not 0 <= bpm <= 300:
        return False

    if not -50 <= temperature <= 100:
        return False

    if not 0 <= spo2 <= 100:
        return False

    return True


def evaluate_sensor_flags(bpm, temperature, spo2):
    """
    Apply the project's configured output thresholds.
    """

    return {
        "temp": TEMP_MIN <= temperature <= TEMP_MAX,
        "bpm": BPM_MIN <= bpm <= BPM_MAX,
        "spo2": SPO2_MIN <= spo2 <= SPO2_MAX
    }


# ============================================================
# SERIAL MESSAGE PROCESSING
# ============================================================

def process_serial_line(line):
    """
    Convert ESP32 messages into events for Main5.py.

    Supported messages:

        V:MATCH:<user_id>
        V:NOMATCH
        H:<bpm>,<temperature>,<spo2>
        MSG:<message>
    """

    timestamp = time.monotonic()

    # --------------------------------------------------------
    # FINGERPRINT MATCH
    # --------------------------------------------------------

    if line.startswith("V:MATCH:"):

        user_id = line.split(":", 2)[2].strip()

        if not user_id:
            print("[SENSORS] Invalid fingerprint user ID.")
            return

        fingerprint_events.put({
            "timestamp": timestamp,
            "verified": True,
            "user_id": user_id
        })

        print(f"[SENSORS] Fingerprint MATCH: User {user_id}")

    # --------------------------------------------------------
    # FINGERPRINT MISMATCH
    # --------------------------------------------------------

    elif line == "V:NOMATCH" or line.startswith("V:NOMATCH:"):

        fingerprint_events.put({
            "timestamp": timestamp,
            "verified": False,
            "user_id": None
        })

        print("[SENSORS] Fingerprint verification FAILED.")

    # --------------------------------------------------------
    # HEALTH SENSOR DATA
    # --------------------------------------------------------

    elif line.startswith("H:"):

        try:
            data = line[2:].split(",")

            if len(data) != 3:
                print("[SENSORS] Invalid health-data format.")
                return

            bpm = int(data[0])
            temperature = float(data[1])
            spo2 = int(data[2])

            if not validate_sensor_data(bpm, temperature, spo2):
                print("[SENSORS] Implausible sensor reading rejected.")
                return

            sensor_flags = evaluate_sensor_flags(
                bpm,
                temperature,
                spo2
            )

            event = {
                "timestamp": timestamp,
                "received": True,
                "bpm": bpm,
                "temperature": temperature,
                "spo2": spo2,
                "flags": sensor_flags
            }

            sensor_events.put(event)

            print(
                f"[SENSORS] BPM={bpm}, "
                f"TEMP={temperature} C, "
                f"SPO2={spo2}%"
            )

        except (ValueError, IndexError) as error:

            print(f"[SENSORS] Could not parse sensor data: {error}")

    # --------------------------------------------------------
    # ESP32 STATUS MESSAGE
    # --------------------------------------------------------

    elif line.startswith("MSG:"):

        print(f"[ESP32] {line[4:]}")


# ============================================================
# BACKGROUND SERIAL LISTENER
# ============================================================

def _serial_listener():

    global listener_error

    try:

        print("[SENSORS] Connecting to ESP32...")

        with serial.Serial(
            SERIAL_PORT,
            BAUD_RATE,
            timeout=0.5
        ) as ser:

            time.sleep(2)

            # Clear startup messages only.
            ser.reset_input_buffer()

            print("[SENSORS] ESP32 connected.")
            print("[SENSORS] Listening for verification events.")

            while not stop_event.is_set():

                try:

                    raw_line = ser.readline()

                    if not raw_line:
                        continue

                    line = raw_line.decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    if line:
                        process_serial_line(line)

                except (ValueError, OSError) as error:

                    print(f"[SENSORS] Serial read error: {error}")
                    raise

    except Exception as error:

        listener_error = error

        if not stop_event.is_set():
            print(f"[SENSORS] Serial listener stopped: {error}")


# ============================================================
# START AND STOP
# ============================================================

def start_listener():

    global listener_thread

    if listener_thread is not None and listener_thread.is_alive():
        return

    stop_event.clear()

    listener_thread = threading.Thread(
        target=_serial_listener,
        daemon=True
    )

    listener_thread.start()


def stop_listener():

    stop_event.set()

    if listener_thread is not None:
        listener_thread.join(timeout=2)

    print("[SENSORS] Listener stopped.")


# ============================================================
# WAIT FOR FINGERPRINT EVENT
# ============================================================

def wait_for_fingerprint(timeout=None):

    while not stop_event.is_set():

        if listener_error is not None:
            raise RuntimeError(
                f"ESP32 listener failed: {listener_error}"
            )

        try:
            return fingerprint_events.get(timeout=0.5)

        except queue.Empty:

            if timeout is not None:
                timeout -= 0.5

                if timeout <= 0:
                    return None

    return None


# ============================================================
# WAIT FOR FRESH SENSOR DATA
# ============================================================

def wait_for_sensor_data(after_timestamp, timeout=10):

    deadline = time.monotonic() + timeout

    while not stop_event.is_set():

        if listener_error is not None:
            raise RuntimeError(
                f"ESP32 listener failed: {listener_error}"
            )

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            return None

        try:

            event = sensor_events.get(
                timeout=min(0.5, remaining)
            )

            # Do not reuse sensor readings from before
            # the current fingerprint event.
            if event["timestamp"] > after_timestamp:
                return event

        except queue.Empty:
            continue

    return None


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    try:

        start_listener()

        while True:

            fingerprint = wait_for_fingerprint()

            if fingerprint is None:
                continue

            print("\nFingerprint event:", fingerprint)

            sensors = wait_for_sensor_data(
                after_timestamp=fingerprint["timestamp"],
                timeout=10
            )

            if sensors is None:
                print("No fresh sensor data received.")
            else:
                print("Sensor event:", sensors)

    except KeyboardInterrupt:

        print("\n[SENSORS] Shutdown requested.")

    finally:

        stop_listener()
