import serial
import time
import RPi.GPIO as GPIO

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0' 
BAUD_RATE = 115200

# Pin Mapping (BCM Numbers)
PIN_TEMP = 18  # Physical Pin 12
PIN_BPM  = 23  # Physical Pin 16
PIN_SPO2 = 24  # Physical Pin 18

# GPIO Initialization
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
pins = [PIN_TEMP, PIN_BPM, PIN_SPO2]

for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW) # Initialize all as LOW

def run_triple_verification():
    print("--- Triple-Signal Biometric Node Active ---")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                data = line.split(',')

                if len(data) == 3:
                    try:
                        bpm = int(data[0])
                        temp = float(data[1])
                        spo2 = int(data[2])
                    except ValueError: continue

                    # --- INDEPENDENT LOGIC ---
                    
                    # 1. Temperature Check (15°C to 45°C)
                    if 15.0 <= temp <= 45.0:
                        GPIO.output(PIN_TEMP, GPIO.HIGH)
                        t_status = "[PASS]"
                    else:
                        GPIO.output(PIN_TEMP, GPIO.LOW)
                        t_status = "[FAIL]"

                    # 2. BPM Check (28 to 200)
                    if 28 <= bpm <= 200:
                        GPIO.output(PIN_BPM, GPIO.HIGH)
                        b_status = "[PASS]"
                    else:
                        GPIO.output(PIN_BPM, GPIO.LOW)
                        b_status = "[FAIL]"

                    # 3. SpO2 Check (75% to 100%)
                    if 75 <= spo2 <= 100:
                        GPIO.output(PIN_SPO2, GPIO.HIGH)
                        s_status = "[PASS]"
                    else:
                        GPIO.output(PIN_SPO2, GPIO.LOW)
                        s_status = "[FAIL]"

                    # Console Output
                    print(f"TEMP: {temp}C {t_status} | BPM: {bpm} {b_status} | SpO2: {spo2}% {s_status}")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        GPIO.cleanup()
        if 'ser' in locals(): ser.close()

if __name__ == "__main__":
    run_triple_verification()
