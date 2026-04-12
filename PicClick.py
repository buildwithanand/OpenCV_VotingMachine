import os
import requests
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

url = "http://127.0.0.1:5000/verify"

face_result_flag = False

def run_once():
    global face_result_flag

    os.system("rpicam-still -o temp.jpg --timeout 1000")

    try:
        files = {"image": open("temp.jpg", "rb")}
        response = requests.post(url, files=files)

        print(response.json())
        result = response.json()

        print(result)

        if result.get("results"):
            status = result["results"][0]["status"]

            if status == "VERIFIED":
                GPIO.output(17, GPIO.HIGH)
                print("GPIO HIGH")
                face_result_flag = True
            else:
                GPIO.output(17, GPIO.LOW)
                print("GPIO LOW")
                face_result_flag = False
        else:
            GPIO.output(17, GPIO.LOW)
            face_result_flag = False

    except Exception as e:
        print("Error:", e)
        GPIO.output(17, GPIO.LOW)
        face_result_flag = False

    time.sleep(2)
