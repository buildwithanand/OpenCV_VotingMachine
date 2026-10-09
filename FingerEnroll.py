#!/usr/bin/env python3
import serial
import time

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

def enroll_user():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
    except Exception as e:
        print(f"Cannot connect to ESP32: {e}")
        return

    user_id = input("Enter new User ID to enroll (1-127): ").strip()
    
    # Send enrollment command to ESP32
    ser.write(f"E{user_id}\n".encode())
    print(f"Sent enrollment command for ID {user_id}. Follow ESP32 instructions below:\n")
    
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if line.startswith("MSG:"):
                print(f"-> {line[4:]}")
            elif "E:SUCCESS" in line:
                print("\n✅ Successfully saved fingerprint to ESP32 memory.")
                break
            elif "E:FAIL" in line:
                print("\n❌ Enrollment failed. Please try again.")
                break

if __name__ == "__main__":
    enroll_user()
