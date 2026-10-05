import cv2
import requests

url = "http://127.0.0.1:5000/verify"

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Save frame temporarily
    cv2.imwrite("temp.jpg", frame)

    # Send to API
    files = {"image": open("temp.jpg", "rb")}
    response = requests.post(url, files=files)

    print(response.json())

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
