from flask import Blueprint, request, jsonify
from bson import ObjectId

ai_explain_bp = Blueprint("ai_explain", __name__)
@ai_explain_bp.route("/", methods=["POST"])
def explain():
    print("AI route hit")

    data = request.get_json()
    print("Received:", data)

    return jsonify({
        "explanation": "यह एक परीक्षण AI उत्तर है।"
    })

@ai_explain_bp.route("/", methods=["POST"])
def explain_scheme():
    try:
        data = request.json
        scheme_id = data.get("schemeId")

        db = request.schemesDB  # injected from app.py

        if not scheme_id:
            return jsonify({
                "explanation": "योजना की जानकारी उपलब्ध नहीं है।"
            })

        scheme = db.schemes.find_one({
            "_id": ObjectId(scheme_id)
        })

        if not scheme:
            return jsonify({
                "explanation": "यह योजना नहीं मिली।"
            })

        # ✅ RULE‑BASED HINDI EXPLANATION (NO AI)
        explanation = f"""
<b>📌 {scheme.get('name')}</b><br><br>

यह एक सरकारी योजना है जो <b>{scheme.get('state')}</b> राज्य के
<b>{scheme.get('category')}</b> वर्ग के लोगों के लिए बनाई गई है।<br><br>

<b>📝 योजना का उद्देश्य:</b><br>
{scheme.get('description', 'जानकारी उपलब्ध नहीं है।')}<br><br>

<b>✅ पात्रता:</b><br>
{', '.join(scheme.get('eligibility', [])) if isinstance(scheme.get('eligibility'), list) else 'जानकारी उपलब्ध नहीं है।'}<br><br>

<b>📄 आवश्यक दस्तावेज़:</b><br>
{', '.join(scheme.get('documents', [])) if isinstance(scheme.get('documents'), list) else 'जानकारी उपलब्ध नहीं है।'}<br><br>

यदि आप पात्र हैं, तो आप इस योजना का लाभ ले सकते हैं।
        """

        return jsonify({ "explanation": explanation })

    except Exception as e:
        print("Explain Error:", e)
        return jsonify({
            "explanation": "योजना का विवरण लोड नहीं हो सका।"
        })