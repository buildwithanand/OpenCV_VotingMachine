import serial
import time
import os

# Update to your specific USB port (e.g., /dev/ttyUSB0 or /dev/ttyACM0)
PORT = '/dev/ttyUSB0' 
BAUD = 115200

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def sanity_check_hardware():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        print(f"Hardware Link Established on {PORT}.")
        print("Awaiting 3-second data buffer...")
        time.sleep(2)

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                data = line.split(',')

                if len(data) == 2:
                    try:
                        bpm = int(data[0])
                        temp = float(data[1])
                    except ValueError:
                        continue # Skip packet if serial data is cut off

                    clear_screen()
                    print("=== ESP32 SENSOR DATA ACQUISITION ===")
                    
                    if bpm == 0 and temp == 0.0:
                        print("Status: IDEAL / WAITING")
                        print("Reason: No IR reflection detected. Place finger on sensor.")
                        print("=====================================")
                        continue

                    print(f"RAW DATA  -> BPM: {bpm} | Temp: {temp}°C\n")
                    print("--- HARDWARE SANITY CHECK ---")

                    # 1. Independent Temperature Check
                    if 15.0 <= temp <= 45.0:
                        print("[PASS] Temperature-verified")
                    else:
                        print("[FAIL] Temperature not verified.")
                        if temp < 15.0:
                            print("       Reason: Value too low. Possible I2C bus drop or sensor obstruction.")
                        elif temp > 45.0:
                            print("       Reason: Value too high. Possible short circuit or direct heat source.")

                    # 2. Independent BPM Check
                    if 28 <= bpm <= 200:
                        print("[PASS] BPM-verified")
                    else:
                        print("[FAIL] BPM not verified.")
                        if bpm < 28:
                            print("       Reason: Value too low. Insufficient optical reflection (press harder).")
                        elif bpm > 200:
                            print("       Reason: Value too high. Optical noise, ambient light bleed, or movement tremor.")
                    
                    print("=====================================")

    except KeyboardInterrupt:
        print("\nProcess terminated.")
    except Exception as e:
        print(f"Serial Fault: {e}")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    sanity_check_hardware()
