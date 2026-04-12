import time
import serial
import RPi.GPIO as GPIO
import adafruit_fingerprint

# --- GPIO PIN DEFINITIONS ---
TOUCH_PIN = 4  # Input from sensor
SIGNAL_PIN = 22 # Output signal to your device (Relay, LED, etc.)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Setup Touch Pin (Input with Pull-Up)
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Setup Output Pin
GPIO.setup(SIGNAL_PIN, GPIO.OUT)
GPIO.output(SIGNAL_PIN, GPIO.LOW) # Ensure it starts OFF

# --- SERIAL SETUP ---
uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

print("--- Fingerprint System: GPIO 22 Output Enabled ---")
print(f"Touch Pin: GPIO {TOUCH_PIN} | Output Pin: GPIO {SIGNAL_PIN}")

try:
    while True:
        # Wait for Touch (LOW)
        if GPIO.input(TOUCH_PIN) == GPIO.LOW:
            print("\nScanning...")
            time.sleep(0.05) # Debounce
            
            if finger.get_image() == adafruit_fingerprint.OK:
                finger.image_2_tz(1)
                
                if finger.finger_search() == adafruit_fingerprint.OK:
                    print(f"MATCH! ID #{finger.finger_id}")
                    
                    # --- TRIGGER OUTPUT SIGNAL ---
                    print("Sending HIGH signal to GPIO 22...")
                    GPIO.output(SIGNAL_PIN, GPIO.HIGH)
                    
                    # Keep signal high for 2 seconds (adjustable)
                    time.sleep(2) 
                    
                    GPIO.output(SIGNAL_PIN, GPIO.LOW)
                    print("GPIO 22 returned to LOW.")
                else:
                    print("ACCESS DENIED.")
            
            # Wait for finger release
            while GPIO.input(TOUCH_PIN) == GPIO.LOW:
                time.sleep(0.1)
            print("Ready.")

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    GPIO.cleanup()
