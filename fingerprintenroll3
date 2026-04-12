import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)

def enroll():
    user_id = input("Enter ID to save (1-127): ")
    ser.write(f"E{user_id}\n".encode())
    
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()
            if line.startswith("MSG:"): print(line[4:])
            elif "E:SUCCESS" in line:
                print("✅ Successfully saved to ESP32 memory.")
                break
            elif "E:FAIL" in line:
                print("❌ Enrollment failed.")
                break

if __name__ == "__main__":
    enroll()
