from flask import Flask, request, jsonify
import numpy as np
import pickle
import cv2
import os

app = Flask(__name__)

# ------------------ CONFIG ------------------
DB_FILE = "aadhaar_sim_db.pkl"
CONF_THRESHOLD = 70   # lower = stricter (LBPH logic)

# ------------------ LOAD DATABASE ------------------
def load_database():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "rb") as f:
        return pickle.load(f)

database = load_database()

# ------------------ SAVE DATABASE ------------------
def save_database():
    with open(DB_FILE, "wb") as f:
        pickle.dump(database, f)

# ------------------ FACE DETECTOR ------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ------------------ CREATE RECOGNIZER ------------------
recognizer = cv2.face.LBPHFaceRecognizer_create()

# ------------------ TRAIN MODEL ------------------
def train_model():
    faces = []
    labels = []
    label_map = {}
    current_id = 0

    for person in database:
        label_map[current_id] = person["name"]

        for img in person["faces"]:
            faces.append(np.array(img, dtype=np.uint8))
            labels.append(current_id)

        current_id += 1

    if len(faces) > 0:
        recognizer.train(faces, np.array(labels))

    return label_map

# ------------------ DETECT FACE ------------------
def detect_face(gray):
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return faces

# ------------------ MATCH ------------------
def match_face(face_img, label_map):
    try:
        label, confidence = recognizer.predict(face_img)

        if confidence < CONF_THRESHOLD:
            return {
                "status": "VERIFIED",
                "name": label_map[label],
                "confidence": round(100 - confidence, 2)
            }
        else:
            return {"status": "NOT VERIFIED"}

    except:
        return {"status": "NOT VERIFIED"}

# ------------------ VERIFY ------------------
@app.route("/verify", methods=["POST"])
def verify_face():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"}), 400

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detect_face(gray)

        if len(faces) == 0:
            return jsonify({"status": "No Face Detected"})

        label_map = train_model()

        results = []

        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            face_img = cv2.resize(face_img, (200, 200))

            result = match_face(face_img, label_map)
            results.append(result)

        return jsonify({
            "faces_detected": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ ADD USER ------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    try:
        if "image" not in request.files or "name" not in request.form:
            return jsonify({"error": "Missing image or name"}), 400

        name = request.form["name"]
        file = request.files["image"]

        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"}), 400

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = detect_face(gray)

        if len(faces) == 0:
            return jsonify({"error": "No face found"}), 400

        (x, y, w, h) = faces[0]
        face_img = gray[y:y+h, x:x+w]
        face_img = cv2.resize(face_img, (200, 200))

        # Check existing user
        for person in database:
            if person["name"] == name:
                person["faces"].append(face_img)
                save_database()
                return jsonify({"message": "Face added to existing user"})

        # New user
        database.append({
            "name": name,
            "faces": [face_img]
        })

        save_database()

        return jsonify({"message": f"{name} added successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ HOME ------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "OpenCV Face Recognition API running 🚀",
        "users": len(database)
    })

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
