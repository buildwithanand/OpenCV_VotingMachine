from flask import Flask, request, jsonify
import face_recognition
import numpy as np
import pickle
import cv2
import os
from camera import start_camera

app = Flask(__name__)

# ------------------ CONFIG ------------------
DB_FILE = "aadhaar_sim_db.pkl"
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

# ------------------ UPDATE CENTROID ------------------
def update_centroid(person):
    encs = np.array(person["encodings"])
    person["centroid"] = np.mean(encs, axis=0)

# ------------------ DYNAMIC THRESHOLD ------------------
def get_dynamic_threshold():
    all_distances = []

    for person in database:
        encs = person["encodings"]
        if len(encs) > 1:
            dists = face_recognition.face_distance(encs[:-1], encs[-1])
            all_distances.extend(dists)

    if len(all_distances) == 0:
        return 0.5

    return min(0.6, np.mean(all_distances) + 0.05)

# ------------------ SMART MATCH ------------------
def match_face(face_encoding):
    best_match = None
    best_score = -1

    for person in database:
        centroid = person.get("centroid")
        if centroid is None:
            continue

        dist = np.linalg.norm(centroid - face_encoding)
        confidence = max(0, (1 - dist)) * 100

        enc_distances = face_recognition.face_distance(
            person["encodings"], face_encoding
        )

        stability = 1 - np.std(enc_distances) if len(enc_distances) > 1 else 1
        final_score = confidence * 0.7 + stability * 30

        if final_score > best_score:
            best_score = final_score
            best_match = person

    threshold = get_dynamic_threshold()

    if best_match and best_score > threshold * 100:
        return {
            "status": "VERIFIED",
            "name": best_match["name"],
            "confidence": round(best_score, 2)
        }

    return {"status": "NOT VERIFIED"}

# ------------------ INTELLIGENT LEARNING ------------------
def update_user_encoding(name, new_encoding):
    for person in database:
        if person["name"] == name:

            encodings = person["encodings"]
            distances = face_recognition.face_distance(encodings, new_encoding)

            if len(distances) > 0:
                min_dist = min(distances)

                if 0.35 < min_dist < 0.6:
                    encodings.append(new_encoding)
            else:
                encodings.append(new_encoding)

            if len(encodings) > MAX_ENCODINGS_PER_USER:
                encodings.pop(0)

            update_centroid(person)
            break

    save_database()

# ------------------ ROUTE: VERIFY IMAGE ------------------
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
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        results = []

        for encoding in face_encodings:
            result = match_face(encoding)
            results.append(result)

            if result["status"] == "VERIFIED" and result["confidence"] > 60:
                update_user_encoding(result["name"], encoding)

        return jsonify({
            "faces_detected": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ ROUTE: LIVE CAMERA ------------------
@app.route("/live", methods=["GET"])
def live_recognition():
    cap = start_camera()

    if cap is None:
        return jsonify({"error": "Camera not accessible"})

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return jsonify({"error": "Capture failed"})

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb)
    encodings = face_recognition.face_encodings(rgb, face_locations)

    results = []

    for encoding in encodings:
        result = match_face(encoding)
        results.append(result)

    return jsonify({
        "faces_detected": len(results),
        "results": results
    })

# ------------------ ROUTE: ADD USER ------------------
@app.route("/add_user", methods=["POST"])
def add_user():
    try:
        if "image" not in request.files or "name" not in request.form:
            return jsonify({"error": "Missing data"}), 400

        name = request.form["name"]

        # Prevent duplicates
        if any(p["name"] == name for p in database):
            return jsonify({"error": "User already exists"}), 400

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
            "encodings": [encodings[0]],
            "centroid": encodings[0]
        }

        database.append(new_person)
        save_database()

        return jsonify({"message": f"{name} added successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ HOME ------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Face AI running 🚀",
        "users": len(database)
    })

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
