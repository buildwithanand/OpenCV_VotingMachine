import serial
import time
import sys

# CONFIGURATION
# On RPi 3B+, the ESP32 usually shows up as /dev/ttyUSB0 or /dev/ttyACM0
SERIAL_PORT = '/dev/ttyUSB0' 
BAUD_RATE = 115200

def run_sanity_checker():
    print("--- Biometric Hardware Sanity Checker ---")
    print(f"Connecting to ESP32 on {SERIAL_PORT}...")
    
    try:
        # Initialize Serial Connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        time.sleep(2) # Allow connection to stabilize
        print("Link Established. Awaiting Data...\n")
        
        while True:
            if ser.in_waiting > 0:
                # Read line and clean up whitespace
                raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Split CSV data: BPM, Temp, SpO2
                parts = raw_line.split(',')
                
                if len(parts) == 3:
                    try:
                        bpm = int(parts[0])
                        temp = float(parts[1])
                        spo2 = int(parts[2])
                    except ValueError:
                        continue # Skip malformed packets

                    print(f"RECEIVED -> BPM: {bpm} | Temp: {temp}C | SpO2: {spo2}%")

                    # 1. Verify Temperature
                    if 15.0 <= temp <= 45.0:
                        print("  [PASS] Temperature-verified")
                    else:
                        print("  [FAIL] Temperature NOT verified (Range: 15-45C)")

                    # 2. Verify BPM
                    if 28 <= bpm <= 200:
                        print("  [PASS] BPM-verified")
                    else:
                        print("  [FAIL] BPM NOT verified (Range: 28-200)")

                    # 3. Verify SpO2
                    if 75 <= spo2 <= 100:
                        print("  [PASS] SpO2-verified")
                    else:
                        print("  [FAIL] SpO2 NOT verified (Range: 75-100%)")
                    
                    print("-" * 40)

    except serial.SerialException as e:
        print(f"Error: Could not open serial port {SERIAL_PORT}. Is the ESP32 plugged in?")
    except KeyboardInterrupt:
        print("\nStopping Sanity Checker...")
    finally:
        if 'ser' in locals():
            ser.close()

if __name__ == "__main__":
    run_sanity_checker()
