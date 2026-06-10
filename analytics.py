from flask import Blueprint, request, jsonify
from datetime import datetime

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/save", methods=["POST"])
def save_analytics():
    try:
        data = request.json

        if not data:
            return jsonify({ "error": "No data provided" }), 400

        # analyticsDB is injected in app.py via before_request
        request.analyticsDB.analytics.insert_one({
            **data,
            "createdAt": datetime.utcnow()
        })

        return jsonify({ "success": True })

    except Exception as e:
        print("Analytics Save Error:", e)
        return jsonify({ "error": "Analytics save failed" }), 500