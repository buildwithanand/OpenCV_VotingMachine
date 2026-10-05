from flask import Flask, request, jsonify
import numpy as np
import pickle
import cv2
import os
from deepface import DeepFace

app = Flask(__name__)

DB_FILE = "face_db.pkl"
THRESHOLD = 0.6  # lower = stricter

# ------------------ LOAD DB ------------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "rb") as f:
        return pickle.load(f)

# ------------------ SAVE DB ------------------
def save_db(db):
    with open(DB_FILE, "wb") as f:
        pickle.dump(db, f)

database = load_db()

# ------------------ GET EMBEDDING ------------------
def get_embedding(img):
    try:
        embedding = DeepFace.represent(
            img_path=img,
            model_name="Facenet",
            enforce_detection=False
        )[0]["embedding"]
        return np.array(embedding)
    except Exception as e:
        print("Embedding error:", e)
        return None

# ------------------ COSINE SIMILARITY ------------------
def cosine_distance(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# ------------------ ADD USER ------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    name = request.form.get("name")

    if "image" not in request.files or not name:
        return jsonify({"error": "Missing name or image"}), 400

    file = request.files["image"]
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    embedding = get_embedding(img)

    if embedding is None:
        return jsonify({"error": "Face not detected"}), 400

    if name in database:
        database[name].append(embedding)
    else:
        database[name] = [embedding]

    save_db(database)

    return jsonify({"message": f"{name} added successfully"})

# ------------------ VERIFY ------------------
@app.route("/verify", methods=["POST"])
def verify():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400

    file = request.files["image"]
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    embedding = get_embedding(img)

    if embedding is None:
        return jsonify({"status": "No face detected"})

    best_match = None
    best_score = -1

    for name, embeddings in database.items():
        for db_emb in embeddings:
            score = cosine_distance(embedding, db_emb)

            if score > best_score:
                best_score = score
                best_match = name

    print("Best Score:", best_score)

    if best_score > THRESHOLD:
        return jsonify({
            "status": "VERIFIED",
            "name": best_match,
            "confidence": round(best_score * 100, 2)
        })
    else:
        return jsonify({
            "status": "UNKNOWN",
            "confidence": round(best_score * 100, 2)
        })

# ------------------ HOME ------------------
@app.route("/")
def home():
    return jsonify({
        "message": "Advanced Face Recognition Running 🚀",
        "users": len(database)
    })

if __name__ == "__main__":
    app.run(debug=True)
