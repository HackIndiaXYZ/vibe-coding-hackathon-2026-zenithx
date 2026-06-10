from flask import Blueprint, request, jsonify
import re

schemes_bp = Blueprint("schemes", __name__)

@schemes_bp.route("/", methods=["GET"])
def get_schemes():
    try:
        category = request.args.get("category")
        state = request.args.get("state")

        if not category or not state:
            return jsonify({ "error": "Missing category or state" }), 400

        # Case-insensitive exact match
        query = {
            "category": { "$regex": f"^{category}$", "$options": "i" },
            "$or": [
                { "state": { "$regex": f"^{state}$", "$options": "i" } },
                { "state": "All" },
                { "state": "India" }
            ]
        }

        schemes = list(
            request.schemesDB.schemes.find(query, { "_id": 0 })
        )

        return jsonify(schemes)

    except Exception as e:
        print("Schemes API Error:", e)
        return jsonify({ "error": "Server error" }), 500