from picamera2 import Picamera2
import cv2
import face_recognition
import numpy as np
import time

# ------------------ LOAD DATABASE ------------------
known_encodings = []
known_names = []

image = face_recognition.load_image_file("faces/shreyon.jpg")
encoding = face_recognition.face_encodings(image)[0]
known_encodings.append(encoding)
known_names.append("Shreyon")

# ------------------ CAMERA ------------------
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
''
''
time.sleep(2)

# ------------------ VARIABLES ------------------
blink_count = 0
head_positions = []
authenticated = False

def eye_aspect_ratio(eye):
    # Simple blink detection logic
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

# ------------------ MAIN LOOP ------------------
while True:
    frame = picam2.capture_array()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    face_encodings = face_recognition.face_encodings(rgb, face_locations)

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

        # -------- FACE MATCH --------
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        name = "Unknown"

        if True in matches:
            name = known_names[matches.index(True)]

        # Draw box
        cv2.rectangle(frame, (left, top), (right, bottom), (0,255,0), 2)
        cv2.putText(frame, name, (left, top-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        # -------- HEAD MOVEMENT (Liveness) --------
        center_x = (left + right) // 2
        head_positions.append(center_x)

        if len(head_positions) > 10:
            head_positions.pop(0)

        if max(head_positions) - min(head_positions) > 40:
            cv2.putText(frame, "Head Movement Detected", (20,50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        # -------- BLINK DETECTION (Simplified) --------
        # (Basic version: using eye region detection is complex → placeholder)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        ).detectMultiScale(gray, 1.3, 5)

        if len(eyes) == 0:
            blink_count += 1
            print("Blink detected:", blink_count)
            time.sleep(0.2)

        # -------- AUTHENTICATION --------
        if blink_count >= 3 and name != "Unknown":
            authenticated = True

        if authenticated:
            cv2.putText(frame, "ACCESS GRANTED", (20,100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 3)
        else:
            cv2.putText(frame, "Blink 3 times", (20,100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

    cv2.imshow("Smart Authentication", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()