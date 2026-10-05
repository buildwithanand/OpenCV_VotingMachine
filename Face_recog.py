from flask import Flask, request, jsonify
import face_recognition
import numpy as np
import pickle
import cv2
import os

app = Flask(__name__)

# ------------------ CONFIG ------------------
DB_FILE = "aadhaar_sim_db.pkl"
THRESHOLD = 0.5
CONFIDENCE_LEARN_THRESHOLD = 60  # Only learn if confidence > 60%
MAX_ENCODINGS_PER_USER = 20

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

# ------------------ MATCH FUNCTION ------------------
def match_face(face_encoding):
    best_match = None
    min_distance = float("inf")

    for person in database:
        enc_list = person.get("encodings", [person.get("encoding")])

        for enc in enc_list:
            dist = face_recognition.face_distance([enc], face_encoding)[0]

            if dist < min_distance:
                min_distance = dist
                best_match = person

    if best_match and min_distance < THRESHOLD:
        return {
            "status": "VERIFIED",
            "name": best_match["name"],
            "confidence": round((1 - min_distance) * 100, 2),
            "distance": min_distance
        }
    else:
        return {
            "status": "NOT VERIFIED"
        }

# ------------------ CONTINUOUS LEARNING ------------------
def update_user_encoding(name, new_encoding):
    for person in database:
        if person["name"] == name:

            # Ensure encodings list exists
            if "encodings" not in person:
                person["encodings"] = [person.get("encoding")]
                person.pop("encoding", None)

            # Avoid duplicates
            distances = face_recognition.face_distance(
                person["encodings"], new_encoding
            )

            if len(distances) == 0 or min(distances) > 0.3:
                person["encodings"].append(new_encoding)

            # Limit size
            if len(person["encodings"]) > MAX_ENCODINGS_PER_USER:
                person["encodings"].pop(0)

            break

    save_database()

# ------------------ ROUTE: VERIFY FACE ------------------
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

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb)

        if len(face_locations) == 0:
            return jsonify({"status": "No Face Detected"})

        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        results = []

        for encoding in face_encodings:
            result = match_face(encoding)
            results.append(result)

            # 🔥 CONTINUOUS LEARNING
            if (
                result["status"] == "VERIFIED"
                and result["confidence"] > CONFIDENCE_LEARN_THRESHOLD
            ):
                update_user_encoding(result["name"], encoding)

        return jsonify({
            "faces_detected": len(results),
            "results": results
        })

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

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        encodings = face_recognition.face_encodings(rgb)

        if len(encodings) == 0:
            return jsonify({"error": "No face found"}), 400

        new_person = {
            "user_id": name,
            "name": name,
            "encodings": [encodings[0]]  # 🔥 multi-encoding structure
        }

        database.append(new_person)
        save_database()

        return jsonify({
            "message": f"{name} added successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ ROUTE: HEALTH CHECK ------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Face Recognition API is running 🚀",
        "users_in_db": len(database)
    })


# ------------------ RUN SERVER ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
