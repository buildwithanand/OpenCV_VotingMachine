from flask import Flask, request, jsonify
from deepface import DeepFace
import numpy as np
import pickle
import cv2
import os

app = Flask(__name__)

# ------------------ CONFIG ------------------
DB_FILE = "aadhaar_sim_db.pkl"
THRESHOLD = 0.6   # DeepFace cosine threshold
MAX_EMBEDDINGS = 15

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

# ------------------ GET EMBEDDING ------------------
def get_embedding(img):
    try:
        embedding = DeepFace.represent(
            img_path=img,
            model_name="Facenet512",
            enforce_detection=True
        )[0]["embedding"]

        return np.array(embedding)
    except:
        return None

# ------------------ MATCH FUNCTION ------------------
def match_face(new_embedding):
    best_match = None
    min_distance = float("inf")

    for person in database:
        for emb in person["embeddings"]:
            dist = np.linalg.norm(new_embedding - emb)

            if dist < min_distance:
                min_distance = dist
                best_match = person

    if best_match and min_distance < THRESHOLD:
        return {
            "status": "VERIFIED",
            "name": best_match["name"],
            "confidence": round((1 - min_distance) * 100, 2)
        }
    else:
        return {
            "status": "NOT VERIFIED"
        }

# ------------------ UPDATE EMBEDDINGS ------------------
def update_embeddings(name, new_embedding):
    for person in database:
        if person["name"] == name:

            distances = [
                np.linalg.norm(new_embedding - emb)
                for emb in person["embeddings"]
            ]

            # Avoid duplicates
            if len(distances) == 0 or min(distances) > 0.4:
                person["embeddings"].append(new_embedding)

            # Limit size
            if len(person["embeddings"]) > MAX_EMBEDDINGS:
                person["embeddings"].pop(0)

            break

    save_database()

# ------------------ ROUTE: VERIFY ------------------
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

        embedding = get_embedding(frame)

        if embedding is None:
            return jsonify({"status": "No Face Detected"})

        result = match_face(embedding)

        # Continuous learning
        if result["status"] == "VERIFIED":
            update_embeddings(result["name"], embedding)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ ROUTE: ADD USER ------------------
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

        embedding = get_embedding(frame)

        if embedding is None:
            return jsonify({"error": "No face found"}), 400

        # Check existing user
        for person in database:
            if person["name"] == name:
                person["embeddings"].append(embedding)
                save_database()
                return jsonify({"message": "Embedding added to existing user"})

        # New user
        database.append({
            "name": name,
            "embeddings": [embedding]
        })

        save_database()

        return jsonify({"message": f"{name} added successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ HEALTH ------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "DeepFace API running 🚀",
        "users": len(database)
    })

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
