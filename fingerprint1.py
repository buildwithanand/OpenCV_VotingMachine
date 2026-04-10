#!/usr/bin/env python3
import argparse
import os
import pickle
import time

import RPi.GPIO as GPIO
from pyfingerprint.pyfingerprint import PyFingerprint

SERIAL_PORT = "/dev/serial0"
BAUDRATE = 57600
PASSWORD = 0xFFFFFFFF

DB_FILE = "finger_db.pkl"

VOTE_OUT_PIN = 18      # goes HIGH when verified
TOUCH_IN_PIN = 23      # TOUCH pin from sensor


def init_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(VOTE_OUT_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TOUCH_IN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def cleanup_gpio():
    GPIO.output(VOTE_OUT_PIN, GPIO.LOW)
    GPIO.cleanup()


def init_sensor():
    try:
        sensor = PyFingerprint(SERIAL_PORT, BAUDRATE, PASSWORD, 0x00000000)
    except Exception as e:
        raise RuntimeError(f"Could not open fingerprint sensor: {e}")

    if not sensor.verifyPassword():
        raise RuntimeError("Fingerprint sensor password verification failed.")

    return sensor


def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            return pickle.load(f)
    return {"slots": {}, "voted": {}}


def save_db(db):
    with open(DB_FILE, "wb") as f:
        pickle.dump(db, f)


def wait_for_touch():
    print("Touch the sensor...")
    while GPIO.input(TOUCH_IN_PIN) == GPIO.HIGH:
        time.sleep(0.05)
    time.sleep(0.2)  # small debounce


def wait_for_finger(sensor):
    while not sensor.readImage():
        time.sleep(0.1)


def enroll(name):
    sensor = init_sensor()
    db = load_db()

    print(f"\nEnrolling: {name}")
    print("Put the finger on the sensor...")

    wait_for_touch()
    wait_for_finger(sensor)
    sensor.convertImage(0x01)

    print("Remove finger...")
    time.sleep(2)
    while GPIO.input(TOUCH_IN_PIN) == GPIO.LOW:
        time.sleep(0.05)

    print("Put the same finger again...")
    wait_for_touch()
    wait_for_finger(sensor)
    sensor.convertImage(0x02)

    if sensor.compareCharacteristics() == 0:
        raise RuntimeError("The two scans do not match. Try again.")

    sensor.createTemplate()
    position_number = sensor.storeTemplate()

    db["slots"][str(position_number)] = name
    db["voted"].setdefault(str(position_number), False)
    save_db(db)

    print(f"Enrolled successfully.")
    print(f"Sensor slot: {position_number}")
    print(f"Saved in: {DB_FILE}")


def verify_and_signal():
    sensor = init_sensor()
    db = load_db()

    print("\nWaiting for touch...")
    wait_for_touch()

    print("Reading fingerprint...")
    wait_for_finger(sensor)
    sensor.convertImage(0x01)

    try:
        position_number, accuracy_score = sensor.searchTemplate()
    except Exception:
        print("No match found.")
        return

    if position_number < 0:
        print("No match found.")
        return

    slot = str(position_number)
    person_name = db["slots"].get(slot, f"Unknown person (slot {slot})")

    if db["voted"].get(slot, False):
        print(f"Match found: {person_name}")
        print("Denied: this person has already voted.")
        return

    print(f"Match found: {person_name}")
    print(f"Confidence: {accuracy_score}")
    print("Vote approved.")

    db["voted"][slot] = True
    save_db(db)

    GPIO.output(VOTE_OUT_PIN, GPIO.HIGH)
    time.sleep(2)
    GPIO.output(VOTE_OUT_PIN, GPIO.LOW)

    print(f"GPIO {VOTE_OUT_PIN} pulsed HIGH.")


def reset_votes():
    db = load_db()
    for k in db["voted"]:
        db["voted"][k] = False
    save_db(db)
    print("Vote status reset.")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_enroll = sub.add_parser("enroll")
    p_enroll.add_argument("name")

    sub.add_parser("verify")
    sub.add_parser("resetvotes")

    args = parser.parse_args()

    init_gpio()
    try:
        if args.command == "enroll":
            enroll(args.name)
        elif args.command == "verify":
            verify_and_signal()
        elif args.command == "resetvotes":
            reset_votes()
    finally:
        cleanup_gpio()


if __name__ == "__main__":
    main()
