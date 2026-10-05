from flask import Flask, request, jsonify
import cv2
import numpy as np
import os
import pickle

app = Flask(__name__)

# ------------------ CONFIG ------------------
DATASET_PATH = "dataset"
MODEL_FILE = "face_model.xml"
LABEL_FILE = "labels.pkl"

os.makedirs(DATASET_PATH, exist_ok=True)

# ------------------ SAFE MODEL CHECK ------------------
if not hasattr(cv2, "face"):
    raise Exception("Install opencv-contrib-python")

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
    if os.path.exists(LABEL_FILE):
        with open(LABEL_FILE, "rb") as f:
            return pickle.load(f)
    return {}

# ------------------ SAVE LABELS ------------------
def save_labels(labels):
    with open(LABEL_FILE, "wb") as f:
        pickle.dump(labels, f)

# ------------------ PREPROCESS ------------------
def preprocess(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

# ------------------ BLUR CHECK ------------------
def is_blurry(image):
    return cv2.Laplacian(image, cv2.CV_64F).var() < 80

# ------------------ FACE ALIGNMENT ------------------
def align_face(gray, face):
    x, y, w, h = face
    roi = gray[y:y+h, x:x+w]

    eyes = eye_cascade.detectMultiScale(roi)

    if len(eyes) >= 2:
        eyes = sorted(eyes, key=lambda x: x[0])[:2]

        (x1, y1, w1, h1), (x2, y2, w2, h2) = eyes

        c1 = (x1 + w1//2, y1 + h1//2)
        c2 = (x2 + w2//2, y2 + h2//2)

        dx, dy = c2[0] - c1[0], c2[1] - c1[1]
        angle = np.degrees(np.arctan2(dy, dx))

        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1)
        roi = cv2.warpAffine(roi, M, (w, h))

    return roi

# ------------------ TRAIN MODEL ------------------
def train_model():
    global model

    faces, labels = [], []
    label_map = load_labels()

    for label, name in label_map.items():
        person_path = os.path.join(DATASET_PATH, name)

        if not os.path.isdir(person_path):
            continue

        for img_name in os.listdir(person_path):
            img_path = os.path.join(person_path, img_name)

            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            faces.append(img)
            labels.append(label)

    if len(faces) < 5:
        return False  # Not enough data

    model = cv2.face.LBPHFaceRecognizer_create()
    model.train(faces, np.array(labels))
    model.save(MODEL_FILE)

    return True

# ------------------ ADD USER ------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    try:
        name = request.form.get("name")
        file = request.files.get("image")

        if not name or not file:
            return jsonify({"error": "Missing name or image"})

        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"})

        gray = preprocess(frame)

        faces = face_cascade.detectMultiScale(gray, 1.2, 5)

        if len(faces) != 1:
            return jsonify({"error": "Exactly one face required"})

        (x, y, w, h) = faces[0]

        face = align_face(gray, (x, y, w, h))
        face = cv2.resize(face, (200, 200))

        if is_blurry(face):
            return jsonify({"error": "Blurry image"})

        # -------- LABEL HANDLING --------
        label_map = load_labels()

        if name not in label_map.values():
            new_label = 0 if not label_map else max(label_map.keys()) + 1
            label_map[new_label] = name
            save_labels(label_map)

        person_path = os.path.join(DATASET_PATH, name)
        os.makedirs(person_path, exist_ok=True)

        count = len(os.listdir(person_path))

        # -------- CONTROLLED AUGMENTATION --------
        cv2.imwrite(f"{person_path}/{count}_orig.jpg", face)
        cv2.imwrite(f"{person_path}/{count}_flip.jpg", cv2.flip(face, 1))

        # -------- TRAIN --------
        trained = train_model()

        return jsonify({
            "message": f"{name} added",
            "model_trained": trained
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# ------------------ VERIFY ------------------
@app.route("/verify", methods=["POST"])
def verify():
    try:
        labels = load_labels()

        if not labels:
            return jsonify({"error": "Model not trained"})

        file = request.files.get("image")

        if not file:
            return jsonify({"error": "No image provided"})

        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Invalid image"})

        gray = preprocess(frame)

        faces = face_cascade.detectMultiScale(gray, 1.2, 5)

        results = []

        for (x, y, w, h) in faces:
            face = align_face(gray, (x, y, w, h))
            face = cv2.resize(face, (200, 200))

            if is_blurry(face):
                results.append({"status": "BLURRY"})
                continue

            label, confidence = model.predict(face)

            if confidence < 60:
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
    return jsonify({"message": "Refined Face AI running 🚀"})

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
