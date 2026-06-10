from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from groq import Groq
import os
import re
from dotenv import load_dotenv
import cv2
import numpy as np
import base64
import uuid
import io
from PIL import Image

load_dotenv()

# ----------------------------------
# APP INIT
# ----------------------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

PORT = 5000
MONGO_URL = "mongodb://127.0.0.1:27017"

haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
print("Haar path:", haar_path)
print("File exists:", os.path.exists(haar_path))

face_cascade = cv2.CascadeClassifier(haar_path)

if face_cascade.empty():
    print("❌ face_cascade failed to load")
else:
    print("✅ face_cascade loaded successfully")

# ----------------------------------
# MONGODB
# ----------------------------------
client      = MongoClient(MONGO_URL)
schemesDB   = client["sarkarsetu"]
analyticsDB = client["sarkar_setu"]

print("✅ MongoDB connected")
print("📦 Total schemes:", schemesDB.schemes.count_documents({}))

# ----------------------------------
# GROQ AI
# ----------------------------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

api_key = os.getenv("GROQ_API_KEY")
print("🔑 GROQ KEY:", api_key[:10] if api_key else "NOT FOUND")

# ----------------------------------
# HELPER: ObjectId to string
# ----------------------------------
def serialize_scheme(scheme):
    scheme["_id"] = str(scheme["_id"])
    return scheme

# ----------------------------------
# HELPER: Groq AI call
# ✅ now accepts optional `question` for voice Q&A
# ----------------------------------
def call_groq_ai(scheme, question=None):
    try:
        if question:
            # Voice Q&A mode — answer the user's specific question
            prompt = f"""एक उपयोगकर्ता ने सरकारी योजना "{scheme.get('name', '')}" के बारे में पूछा है।

योजना विवरण: {scheme.get('description', '')}
पात्रता: {scheme.get('eligibility', '')}
श्रेणी: {scheme.get('category', '')}
राज्य: {scheme.get('state', 'सभी राज्य')}

उपयोगकर्ता का प्रश्न: {question}

2 से 3 सरल हिंदी वाक्यों में उत्तर दें। कोई emoji या विशेष चिन्ह उपयोग न करें।"""
        else:
            # Explanation mode — explain the scheme
            prompt = f"""आप एक सरकारी योजना सहायक हैं। नीचे दी गई सरकारी योजना को सरल हिंदी में समझाएं।

योजना का नाम: {scheme.get('name', 'अज्ञात')}
श्रेणी: {scheme.get('category', '')}
राज्य: {scheme.get('state', 'सभी राज्य')}
विवरण: {scheme.get('description', '')}
पात्रता: {scheme.get('eligibility', '')}

नीचे दिए गए फॉर्मेट में उत्तर दें। कोई emoji या विशेष चिन्ह उपयोग न करें। केवल सादा हिंदी टेक्स्ट लिखें।

योजना क्या है:
[2-3 सरल वाक्य]

मुख्य लाभ:
- [लाभ 1]
- [लाभ 2]
- [लाभ 3]

कौन आवेदन कर सकता है:
[पात्रता सरल शब्दों में]

आवेदन कैसे करें:
- [चरण 1]
- [चरण 2]

कितना पैसा मिलेगा या क्या फायदा होगा:
[लाभ की राशि या सुविधा]"""

        chat = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "आप एक सरकारी योजना सहायक हैं। हमेशा केवल सादा हिंदी में उत्तर दें। कभी भी emoji, स्टार (*), हैश (#) या कोई विशेष चिन्ह उपयोग न करें।"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=600,
            temperature=0.7
        )

        text = chat.choices[0].message.content
        text = re.sub(r'[^\w\s\u0900-\u097F\n\-:,।.()/]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        return text

    except Exception as e:
        print("Groq Error:", e)
        return f"AI सेवा में त्रुटि: {str(e)}"

# ----------------------------------
# SCHEMES API
# ----------------------------------
@app.route("/api/schemes", methods=["GET"])
def get_schemes():
    try:
        category = request.args.get("category", "").strip()
        state    = request.args.get("state", "").strip()

        print(f"Query — category: '{category}', state: '{state}'")

        if not category or not state:
            return jsonify({"error": "Missing category or state"}), 400

        schemes = list(
            schemesDB.schemes.find({
                "category": {"$regex": f"^{category}$", "$options": "i"},
                "$or": [
                    {"state": {"$regex": f"^{state}$",   "$options": "i"}},
                    {"state": {"$regex": "^All India$",  "$options": "i"}},
                    {"state": {"$regex": "^All$",        "$options": "i"}},
                    {"state": ""},
                    {"state": {"$exists": False}}
                ]
            })
        )

        print(f"Found {len(schemes)} schemes")
        schemes = [serialize_scheme(s) for s in schemes]
        return jsonify(schemes)

    except Exception as e:
        print("Schemes Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# AI EXPLAIN API
# ✅ now handles optional `question` field for voice Q&A
# ----------------------------------
@app.route("/api/ai-explain", methods=["POST"])
def ai_explain():
    try:
        data     = request.json or {}
        scheme   = data.get("scheme", {})
        question = data.get("question", None)  # ✅ voice Q&A question

        if not scheme:
            return jsonify({"error": "No scheme data"}), 400

        if question:
            print(f"Voice Q&A: '{question}' about {scheme.get('name')}")
        else:
            print("AI explaining:", scheme.get("name"))

        explanation = call_groq_ai(scheme, question)
        return jsonify({"explanation": explanation})

    except Exception as e:
        print("AI Route Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# ANALYTICS
# ----------------------------------
@app.route("/api/analytics", methods=["POST"])
def save_analytics():
    try:
        data = request.json
        document = {
            "category":  data.get("category", ""),
            "state":     data.get("state", ""),
            "income":    data.get("income", ""),
            "ration":    data.get("ration", ""),
            "timestamp": data.get("timestamp", ""),
            "createdAt": datetime.utcnow()
        }
        analyticsDB.analytics.insert_one(document)
        print(f"Analytics saved: {document['category']} | {document['state']} | {document['income']}")
        return jsonify({"success": True})

    except Exception as e:
        print("Analytics Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# DASHBOARD — category
# ----------------------------------
@app.route("/api/dashboard/category", methods=["GET"])
def dashboard_category():
    try:
        data = list(analyticsDB.analytics.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        return jsonify(data)
    except Exception as e:
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — state
# ----------------------------------
@app.route("/api/dashboard/state", methods=["GET"])
def dashboard_state():
    try:
        data = list(analyticsDB.analytics.aggregate([
            {"$group": {"_id": "$state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        return jsonify(data)
    except Exception as e:
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — schemes
# ----------------------------------
@app.route("/api/dashboard/schemes", methods=["GET"])
def dashboard_schemes():
    try:
        data = list(analyticsDB.analytics.aggregate([
            {"$group": {"_id": "$schemeName", "views": {"$sum": 1}}},
            {"$sort": {"views": -1}}
        ]))
        return jsonify(data)
    except Exception as e:
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — income
# ----------------------------------
@app.route("/api/dashboard/income", methods=["GET"])
def dashboard_income():
    try:
        data = list(analyticsDB.analytics.aggregate([
            {"$group": {"_id": "$income", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        return jsonify(data)
    except Exception as e:
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — ration
# ----------------------------------
@app.route("/api/dashboard/ration", methods=["GET"])
def dashboard_ration():
    try:
        data = list(analyticsDB.analytics.aggregate([
            {"$group": {"_id": "$ration", "count": {"$sum": 1}}}
        ]))
        return jsonify(data)
    except Exception as e:
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — budget
# ----------------------------------
@app.route("/api/dashboard/budget", methods=["GET"])
def dashboard_budget():
    try:
        income_budget_map = {
            "below50": 12000,
            "50-1":    10000,
            "1-3":     8000,
            "3-5":     6000,
            "above5":  4000
        }

        data = list(analyticsDB.analytics.aggregate([
            {
                "$group": {
                    "_id": {
                        "state":    "$state",
                        "category": "$category",
                        "income":   "$income"
                    },
                    "users": {"$sum": 1}
                }
            },
            {
                "$project": {
                    "_id":      0,
                    "state":    "$_id.state",
                    "category": "$_id.category",
                    "income":   "$_id.income",
                    "users":    1
                }
            },
            {"$sort": {"users": -1}}
        ]))

        for row in data:
            per_person             = income_budget_map.get(row.get("income", ""), 6000)
            row["perPersonBudget"] = per_person
            row["estimatedBudget"] = per_person * row["users"]

        return jsonify(data)

    except Exception as e:
        print("Budget Error:", e)
        return jsonify([]), 500

# ----------------------------------
# DASHBOARD — all records
# ----------------------------------
@app.route("/api/dashboard/records", methods=["GET"])
def dashboard_records():
    try:
        limit = int(request.args.get("limit", 200))
        data  = list(
            analyticsDB.analytics
            .find({}, {"_id": 0})
            .sort("createdAt", -1)
            .limit(limit)
        )
        for row in data:
            if "createdAt" in row:
                row["createdAt"] = str(row["createdAt"])
        return jsonify(data)

    except Exception as e:
        print("Records Error:", e)
        return jsonify([]), 500

# ----------------------------------
# AI CHAT
# ----------------------------------
@app.route("/api/chat", methods=["POST"])
def ai_chat():
    try:
        data    = request.json or {}
        message = data.get("message", "")
        context = data.get("context", "")
        history = data.get("history", [])

        if not message:
            return jsonify({"error": "No message"}), 400

        messages = [
            {
                "role": "system",
                "content": f"""आप सरकार सेतु के AI सहायक हैं।
केवल सरकारी योजनाओं के बारे में सरल हिंदी में उत्तर दें।
उत्तर बहुत छोटा रखें — 2 से 3 वाक्य।
कोई emoji या विशेष चिन्ह उपयोग न करें।
वर्तमान संदर्भ: {context}"""
            }
        ]

        for h in history[-6:]:
            if h.get("role") in ["user", "assistant"]:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": message})

        chat = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            max_tokens=200,
            temperature=0.7
        )

        reply = chat.choices[0].message.content
        reply = re.sub(r'[^\w\s\u0900-\u097F\n\-:,।.()/]', '', reply)
        reply = re.sub(r'\n{3,}', '\n\n', reply).strip()

        return jsonify({"reply": reply})

    except Exception as e:
        print("Chat Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# FACE IDENTIFY
# ----------------------------------
@app.route("/api/face/identify", methods=["POST"])
def face_identify():
    try:
        data       = request.json or {}
        image_data = data.get("image", "")

        if not image_data:
            return jsonify({"error": "No image received"}), 400

        if "," in image_data:
            image_data = image_data.split(",")[1]

        image_bytes = base64.b64decode(image_data)
        image       = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        np_image    = np.array(image)
        gray        = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)

        face_cascade_local = cv2.CascadeClassifier(
            os.path.join(os.path.dirname(cv2.__file__), "data", "haarcascade_frontalface_default.xml")
        )

        faces = face_cascade_local.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )

        if len(faces) == 0:
            return jsonify({"status": "no_face"})

        x, y, w, h  = max(faces, key=lambda f: f[2] * f[3])
        face_region = gray[y:y+h, x:x+w]
        face_resized = cv2.resize(face_region, (200, 200))
        face_eq     = cv2.equalizeHist(face_resized)

        def get_face_signature(img):
            h, w = img.shape
            regions = [
                img[0:h//2,          0:w//2],
                img[0:h//2,          w//2:w],
                img[h//2:h,          0:w//2],
                img[h//2:h,          w//2:w],
                img[h//4:3*h//4, w//4:3*w//4],
            ]
            sig = []
            for region in regions:
                hist = cv2.calcHist([region], [0], None, [64], [0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                sig.extend(hist.tolist())
            return sig

        current_sig = get_face_signature(face_eq)

        all_users   = list(analyticsDB.face_users.find({}))
        best_match  = None
        best_score  = float("inf")
        MATCH_THRESHOLD = 1.8

        for user in all_users:
            saved_sig = np.array(user.get("faceSignature", []), dtype=np.float32)
            if len(saved_sig) == 0:
                continue
            curr_arr = np.array(current_sig, dtype=np.float32)
            score    = float(np.linalg.norm(curr_arr - saved_sig))
            print(f"  Score vs {user['userId']}: {score:.3f}")
            if score < best_score:
                best_score = score
                best_match = user

        print(f"  Best score: {best_score:.3f} (threshold: {MATCH_THRESHOLD})")

        if best_match and best_score < MATCH_THRESHOLD:
            saved_sig   = np.array(best_match["faceSignature"], dtype=np.float32)
            curr_arr    = np.array(current_sig,                 dtype=np.float32)
            updated_sig = ((saved_sig * 0.7) + (curr_arr * 0.3)).tolist()

            analyticsDB.face_users.update_one(
                {"userId": best_match["userId"]},
                {"$set": {"faceSignature": updated_sig}}
            )

            print(f"✅ Login: {best_match['userId']} score={best_score:.3f}")
            return jsonify({
                "status":  "login",
                "userId":  best_match["userId"],
                "message": "Welcome back!"
            })

        new_id = "user_" + str(uuid.uuid4())[:8]
        analyticsDB.face_users.insert_one({
            "userId":        new_id,
            "faceSignature": current_sig,
            "createdAt":     datetime.utcnow()
        })

        print(f"🆕 Registered: {new_id} (best score was: {best_score:.3f})")
        return jsonify({
            "status":  "register",
            "userId":  new_id,
            "message": "Registered successfully!"
        })

    except Exception as e:
        print("Face Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# NEARBY JAN SEVA KENDRA API
# Uses OpenStreetMap Overpass — free, no key needed
# ----------------------------------
@app.route("/api/nearby-jsk", methods=["GET"])
def nearby_jsk():
    try:
        import requests as req

        lat = request.args.get("lat", "")
        lon = request.args.get("lon", "")
        radius = int(request.args.get("radius", 2000))  # default 2km

        if not lat or not lon:
            return jsonify({"error": "Missing lat/lon"}), 400

        lat, lon = float(lat), float(lon)

        # Overpass query — finds CSC / Jan Seva Kendra / government offices
        overpass_query = f"""
[out:json][timeout:15];
(
  node["amenity"="government"]["name"~"Jan Seva|CSC|Common Service|Sewa Kendra|सेवा केंद्र",i](around:{radius},{lat},{lon});
  node["office"="government"]["name"~"Jan Seva|CSC|Common Service|Sewa Kendra|सेवा केंद्र",i](around:{radius},{lat},{lon});
  node["name"~"Jan Seva Kendra|Common Service Centre|CSC|Sewa Kendra",i](around:{radius},{lat},{lon});
);
out body 10;
"""

        response = req.post(
            "https://overpass-api.de/api/interpreter",
            data=overpass_query,
            timeout=15
        )
        data = response.json()

        results = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:hi") or "Jan Seva Kendra"
            results.append({
                "name":    name,
                "lat":     el["lat"],
                "lon":     el["lon"],
                "address": tags.get("addr:full") or tags.get("addr:street") or tags.get("addr:city") or "",
                "phone":   tags.get("phone") or tags.get("contact:phone") or ""
            })

        # If OSM returns nothing, fall back to Groq-generated nearby suggestions
        if not results:
            prompt = f"""List 3 likely Jan Seva Kendra or Common Service Centre locations near latitude {lat}, longitude {lon} in India.
For each give: name, approximate address (area/district name), and distance estimate.
Reply ONLY as JSON array like: [{{"name":"...", "address":"...", "lat":{lat}, "lon":{lon}, "note":"approximate"}}]
No explanation, just JSON."""

            chat = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                max_tokens=300
            )
            raw = chat.choices[0].message.content.strip()
            # extract JSON array
            import json as json_lib
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                results = json_lib.loads(match.group())

        return jsonify({"centers": results, "userLat": lat, "userLon": lon})

    except Exception as e:
        print("JSK Error:", e)
        return jsonify({"error": str(e)}), 500

# ----------------------------------
# SERVE FRONTEND
# ----------------------------------

@app.route("/<path:filename>")
def serve_static(filename):
    frontend = os.path.join(os.path.dirname(__file__), "frontend")
    return send_from_directory(frontend, filename)

# ----------------------------------
# SERVER START
# ----------------------------------
if __name__ == "__main__":
    app.run(port=PORT, debug=True)