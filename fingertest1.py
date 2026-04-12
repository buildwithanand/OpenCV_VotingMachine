import time
import serial
import RPi.GPIO as GPIO
import adafruit_fingerprint

# --- GPIO SETUP ---
TOUCH_PIN = 4
GPIO.setmode(GPIO.BCM)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- SERIAL SETUP ---
try:
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)
except Exception as e:
    print(f"Error: {e}")
    exit()

def enroll_mode():
    print("\n--- ENROLLMENT MODE ---")
    id_num = int(input("Enter ID # (1-1000) to save as: "))
    
    print("Waiting for finger to enroll...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Image taken. Remove finger.")
    finger.image_2_tz(1)
    time.sleep(2)
    
    print("Place same finger again...")
    while finger.get_image() != adafruit_fingerprint.OK:
        pass
    print("Image taken.")
    finger.image_2_tz(2)
    
    if finger.create_model() == adafruit_fingerprint.OK:
        if finger.store_model(id_num) == adafruit_fingerprint.OK:
            print(f"Successfully stored ID #{id_num}!")
        else:
            print("Failed to store.")
    else:
        print("Prints did not match.")

def verify_mode():
    print("\n--- VERIFICATION MODE (Ready for touch) ---")
    while True:
        if GPIO.input(TOUCH_PIN) == GPIO.LOW:
            print("Touch detected! Scanning...")
            if finger.get_image() == adafruit_fingerprint.OK:
                finger.image_2_tz(1)
                if finger.finger_search() == adafruit_fingerprint.OK:
                    print(f"MATCH FOUND: ID #{finger.finger_id} (Score: {finger.confidence})")
                else:
                    print("Unknown finger.")
            
            while GPIO.input(TOUCH_PIN) == GPIO.LOW:
                time.sleep(0.1)
            print("Ready for next user...")
        time.sleep(0.05)

# --- MAIN MENU ---
try:
    if finger.read_sysparam():
        print("Sensor Found!")
        choice = input("Select Mode: [E]nroll or [V]erify: ").upper()
        if choice == 'E':
            enroll_mode()
        elif choice == 'V':
            verify_mode()
except KeyboardInterrupt:
    print("\nExiting.")
finally:
    GPIO.cleanup()
