import time
import serial
import adafruit_fingerprint

# --- SERIAL SETUP ---
# Pi 3B+ uses /dev/serial0 for GPIO pins 8 & 10
uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

def get_enrollment():
    """Guided enrollment process"""
    try:
        id_num = int(input("\nEnter the ID # (1-1000) for this finger: "))
    except ValueError:
        print("Invalid ID. Please enter a number.")
        return False

    print("Step 1: Place finger on sensor...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    
    print("Image taken. Converting...")
    if finger.image_2_tz(1) != adafruit_fingerprint.OK:
        print("Image too messy. Try again.")
        return False

    print("Step 2: Remove finger.")
    time.sleep(2)
    while finger.get_image() != adafruit_fingerprint.NOFINGER:
        pass

    print("Place the SAME finger again...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass

    print("Image taken. Converting...")
    if finger.image_2_tz(2) != adafruit_fingerprint.OK:
        print("Image failed. Try again.")
        return False

    print("Creating model...")
    if finger.create_model() != adafruit_fingerprint.OK:
        print("Prints did not match. Enrollment aborted.")
        return False

    print(f"Storing model as ID #{id_num}...")
    if finger.store_model(id_num) == adafruit_fingerprint.OK:
        print("STORED SUCCESSFULLY!")
        return True
    else:
        print("Storage error.")
        return False

# --- MAIN RUN ---
if finger.read_sysparam():
    print("Sensor Found! Capacity:", finger.capacity)
    while True:
        if get_enrollment():
            cont = input("Enroll another? (y/n): ").lower()
            if cont != 'y': break
else:
    print("Sensor not found. Check wiring or raspi-config.")
