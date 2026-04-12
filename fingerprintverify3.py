import serial
import RPi.GPIO as GPIO
import time

OUTPUT_PIN = 22 # To your relay/lock
GPIO.setmode(GPIO.BCM)
GPIO.setup(OUTPUT_PIN, GPIO.OUT)

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

def main():
    print("Verification Mode Active.")
    while True:
        ser.write(b'V') # Trigger a verify request
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode().strip()
                if "V:MATCH" in line:
                    print(f"Verified! ID: {line.split(':')[-1]}")
                    GPIO.output(OUTPUT_PIN, GPIO.HIGH)
                    time.sleep(2)
                    GPIO.output(OUTPUT_PIN, GPIO.LOW)
                    break
                elif "V:NOMATCH" in line or "V:FAIL" in line:
                    print("Access Denied.")
                    break
        time.sleep(0.5)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: GPIO.cleanup()
