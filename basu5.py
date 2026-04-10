from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
import pickle

app = Flask(__name__)

# ------------------ CONFIG ------------------
DATASET_PATH = "dataset"
MODEL_FILE = "face_model.xml"

# Create dataset folder
os.makedirs(DATASET_PATH, exist_ok=True)

# ------------------ FACE DETECTOR ------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ------------------ LOAD MODEL ------------------
def load_model():
    if os.path.exists(MODEL_FILE):
        model = cv2.face.LBPHFaceRecognizer_create()
        model.read(MODEL_FILE)
        return model
    return cv2.face.LBPHFaceRecognizer_create()

model = load_model()

# ------------------ TRAIN MODEL ------------------
def train_model():
    faces = []
    labels = []
    label_map = {}
    current_label = 0

    for person_name in os.listdir(DATASET_PATH):
        person_path = os.path.join(DATASET_PATH, person_name)

        if not os.path.isdir(person_path):
            continue

        label_map[current_label] = person_name

        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)

            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            faces.append(img)
            labels.append(current_label)

        current_label += 1

    if len(faces) > 0:
        model.train(faces, np.array(labels))
        model.save(MODEL_FILE)

        with open("labels.pkl", "wb") as f:
            pickle.dump(label_map, f)

# ------------------ LOAD LABELS ------------------
def load_labels():
    if os.path.exists("labels.pkl"):
        with open("labels.pkl", "rb") as f:
            return pickle.load(f)
    return {}

# ------------------ ADD USER ------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    try:
        name = request.form["name"]
        file = request.files["image"]

        person_path = os.path.join(DATASET_PATH, name)
        os.makedirs(person_path, exist_ok=True)

        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 0:
            return jsonify({"error": "No face detected"})

        for i, (x, y, w, h) in enumerate(faces):
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            cv2.imwrite(f"{person_path}/{len(os.listdir(person_path))}.jpg", face)

        train_model()

        return jsonify({"message": f"{name} added and trained"})

    except Exception as e:
        return jsonify({"error": str(e)})

# ------------------ VERIFY ------------------
@app.route("/verify", methods=["POST"])
def verify():
    try:
        labels = load_labels()

        file = request.files["image"]
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        results = []

        for (x, y, w, h) in faces:
            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            label, confidence = model.predict(face)

            if confidence < 80:
                name = labels.get(label, "Unknown")
                results.append({
                    "status": "VERIFIED",
                    "name": name,
                    "confidence": round(100 - confidence, 2)
                })
            else:
                results.append({"status": "NOT VERIFIED"})

        return jsonify({
            "faces_detected": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# ------------------ HOME ------------------
@app.route("/")
def home():
    return jsonify({"message": "OpenCV Face AI running 🚀"})

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
