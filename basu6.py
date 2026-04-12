from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
import pickle

app = Flask(__name__)

# ------------------ CONFIG ------------------
DATASET_PATH = "dataset"
MODEL_FILE = "face_model.xml"

os.makedirs(DATASET_PATH, exist_ok=True)

# ------------------ FACE DETECTORS ------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

eye_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_eye.xml"
)

# ------------------ LOAD MODEL ------------------
def load_model():
    model = cv2.face.LBPHFaceRecognizer_create()
    if os.path.exists(MODEL_FILE):
        model.read(MODEL_FILE)
    return model

model = load_model()

# ------------------ LOAD LABELS ------------------
def load_labels():
    if os.path.exists("labels.pkl"):
        with open("labels.pkl", "rb") as f:
            return pickle.load(f)
    return {}

# ------------------ BLUR CHECK ------------------
def is_blurry(image):
    return cv2.Laplacian(image, cv2.CV_64F).var() < 100

# ------------------ FACE ALIGNMENT ------------------
def align_face(gray, face):
    x, y, w, h = face
    roi = gray[y:y+h, x:x+w]

    eyes = eye_cascade.detectMultiScale(roi)

    if len(eyes) >= 2:
        eyes = sorted(eyes, key=lambda x: x[0])
        eye1 = eyes[0]
        eye2 = eyes[1]

        ex1, ey1, ew1, eh1 = eye1
        ex2, ey2, ew2, eh2 = eye2

        center1 = (ex1 + ew1//2, ey1 + eh1//2)
        center2 = (ex2 + ew2//2, ey2 + eh2//2)

        dx = center2[0] - center1[0]
        dy = center2[1] - center1[1]

        angle = np.degrees(np.arctan2(dy, dx))

        center = (w//2, h//2)
        M = cv2.getRotationMatrix2D(center, angle, 1)

        aligned = cv2.warpAffine(roi, M, (w, h))
        return aligned

    return roi

# ------------------ TRAIN MODEL ------------------
def train_model():
    global model

    faces = []
    labels = []
    label_map = load_labels()

    current_label = 0 if not label_map else max(label_map.keys()) + 1

    for person_name in os.listdir(DATASET_PATH):
        person_path = os.path.join(DATASET_PATH, person_name)

        if not os.path.isdir(person_path):
            continue

        # reuse existing label if present
        existing_label = None
        for k, v in label_map.items():
            if v == person_name:
                existing_label = k
                break

        if existing_label is None:
            label = current_label
            label_map[label] = person_name
            current_label += 1
        else:
            label = existing_label

        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)

            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            faces.append(img)
            labels.append(label)

    if len(faces) > 0:
        model = cv2.face.LBPHFaceRecognizer_create()
        model.train(faces, np.array(labels))
        model.save(MODEL_FILE)

        with open("labels.pkl", "wb") as f:
            pickle.dump(label_map, f)

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
        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) != 1:
            return jsonify({"error": "Exactly one face required"})

        (x, y, w, h) = faces[0]

        face = align_face(gray, (x, y, w, h))
        face = cv2.resize(face, (200, 200))

        if is_blurry(face):
            return jsonify({"error": "Image too blurry"})

        base_path = f"{person_path}/{len(os.listdir(person_path))}"

        # Data augmentation
        cv2.imwrite(base_path + "_orig.jpg", face)
        cv2.imwrite(base_path + "_flip.jpg", cv2.flip(face, 1))
        cv2.imwrite(base_path + "_bright.jpg",
                    cv2.convertScaleAbs(face, alpha=1.2, beta=20))
        cv2.imwrite(base_path + "_dark.jpg",
                    cv2.convertScaleAbs(face, alpha=0.8, beta=-20))

        train_model()

        return jsonify({"message": f"{name} added & trained successfully"})

    except Exception as e:
        return jsonify({"error": str(e)})

# ------------------ VERIFY ------------------
@app.route("/verify", methods=["POST"])
def verify():
    try:
        labels = load_labels()

        if len(labels) == 0:
            return jsonify({"error": "Model not trained yet"})

        file = request.files["image"]
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        results = []

        for (x, y, w, h) in faces:
            face = align_face(gray, (x, y, w, h))
            face = cv2.resize(face, (200, 200))

            if is_blurry(face):
                results.append({"status": "BLURRY IMAGE"})
                continue

            label, confidence = model.predict(face)

            if confidence < 65:
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
    return jsonify({"message": "Enhanced Face AI running 🚀"})

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
