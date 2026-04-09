import os
import requests
import time

url = "http://127.0.0.1:5000/verify"

while True:
    # Capture image using Pi camera
    os.system("rpicam-still -o temp.jpg --timeout 1000")

    # Send to API
    try:
        files = {"image": open("temp.jpg", "rb")}
        response = requests.post(url, files=files)
        print(response.json())
    except Exception as e:
        print("Error:", e)

    time.sleep(2)
