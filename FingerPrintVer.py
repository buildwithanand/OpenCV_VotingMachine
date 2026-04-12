import serial
import RPi.GPIO as GPIO
import time

OUTPUT_PIN = 22
GPIO.setmode(GPIO.BCM)
GPIO.setup(OUTPUT_PIN, GPIO.OUT)

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

fingerprint_result_flag = False

def run_once():
    global fingerprint_result_flag

    print("Verification Mode Active.")

    ser.write(b'V')

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()

            if "V:MATCH" in line:
                print(f"Verified! ID: {line.split(':')[-1]}")
                GPIO.output(OUTPUT_PIN, GPIO.HIGH)
                time.sleep(2)
                GPIO.output(OUTPUT_PIN, GPIO.LOW)
                fingerprint_result_flag = True
                return True

            elif "V:NOMATCH" in line or "V:FAIL" in line:
                print("Access Denied.")
                fingerprint_result_flag = False
                return False
