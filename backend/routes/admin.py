from flask import Blueprint, request, jsonify
from services.database import (
    get_all_entries,
    add_entry,
    update_entry,
    delete_entry,
    get_chat_logs,
    get_topic_stats,
    db
)

admin_bp = Blueprint("admin", __name__)


# ── Protect all admin routes with a simple secret key ────────
def check_admin_key():
    """
    Simple admin authentication.
    Checks against master SECRET_KEY or Firebase stored password.
    """
    data = request.get_json(silent=True) or {}
    key = data.get("admin_key") or request.headers.get("X-Admin-Key") or request.args.get("admin_key")
    import os
    master = os.getenv("SECRET_KEY")
    if key == master:
        return True
    try:
        stored = db.collection("settings").document("admin").get()
        if stored.exists:
            return key == stored.to_dict().get("password", master)
    except Exception:
        pass
    return False


# ── Knowledge Base Management ─────────────────────────────────
@admin_bp.route("/admin/entries", methods=["GET"])
def get_entries():
    """Get all knowledge base entries for the admin panel."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        entries = get_all_entries()
        return jsonify({"entries": entries, "count": len(entries)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/entries", methods=["POST"])
def create_entry():
    """Add a new knowledge base entry."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()

        # Validate required fields
        required = ["topic", "question", "answer"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"'{field}' is required."}), 400

        entry_id = add_entry(
            topic=data["topic"],
            question=data["question"],
            answer=data["answer"],
            keywords=data.get("keywords", "")
        )
        return jsonify({
            "message": "Entry added successfully.",
            "id": entry_id
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/entries/<entry_id>", methods=["PUT"])
def edit_entry(entry_id):
    """Update an existing knowledge base entry."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()

        # Only allow these fields to be updated
        allowed = ["topic", "question", "answer", "keywords", "active"]
        updates = {k: v for k, v in data.items() if k in allowed}

        if not updates:
            return jsonify({"error": "No valid fields to update."}), 400

        update_entry(entry_id, updates)
        return jsonify({"message": "Entry updated successfully."}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/entries/<entry_id>", methods=["DELETE"])
def remove_entry(entry_id):
    """Soft delete a knowledge base entry (sets active=False)."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        delete_entry(entry_id)
        return jsonify({"message": "Entry deactivated successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Analytics ─────────────────────────────────────────────────
@admin_bp.route("/admin/logs", methods=["GET"])
def chat_logs():
    """Get recent student conversations for review."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        limit = request.args.get("limit", 50, type=int)
        logs = get_chat_logs(limit=limit)
        return jsonify({"logs": logs, "count": len(logs)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/admin/stats", methods=["GET"])
def stats():
    """Get question counts per topic for the analytics dashboard."""
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        topic_stats = get_topic_stats()
        total = sum(topic_stats.values())
        from services.database import db
        feedback_docs = list(db.collection("feedback").stream())
        thumbs_up = sum(1 for d in feedback_docs if d.to_dict().get("rating") == "up")
        thumbs_down = sum(1 for d in feedback_docs if d.to_dict().get("rating") == "down")
        return jsonify({
            "total_questions": total,
            "by_topic": topic_stats,
            "feedback": {
                "total": len(feedback_docs),
                "thumbs_up": thumbs_up,
                "thumbs_down": thumbs_down,
                "satisfaction_rate": round((thumbs_up / len(feedback_docs)) * 100) if feedback_docs else 0
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── File Upload & AI Extraction ───────────────────────────────
@admin_bp.route("/admin/upload", methods=["POST"])
def upload_file():
    """Upload a JSON file of Q&A pairs directly into the knowledge base."""
    data = request.get_json(silent=True) or {}
    if not check_admin_key():
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename.lower()

    if not filename.endswith(".json"):
        return jsonify({"error": "Only JSON files are supported. Format: [{topic, question, answer, keywords}]"}), 400

    try:
        import json
        raw = file.read().decode("utf-8", errors="ignore")
        entries = json.loads(raw)

        if not isinstance(entries, list):
            return jsonify({"error": "JSON must be an array of entries."}), 400

        valid = []
        for e in entries:
            if e.get("question") and e.get("answer") and e.get("topic"):
                valid.append({
                    "topic": e.get("topic", "general"),
                    "question": e["question"],
                    "answer": e["answer"],
                    "keywords": e.get("keywords", "")
                })

        if not valid:
            return jsonify({"error": "No valid entries found. Each entry needs topic, question and answer."}), 400

        return jsonify({"entries": valid, "count": len(valid)}), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON file. Please check the file format."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/admin/password", methods=["GET"])
def get_password():
    import os
    try:
        doc = db.collection("settings").document("admin").get()
        if doc.exists:
            return jsonify({"password": doc.to_dict().get("password", os.getenv("SECRET_KEY"))}), 200
        return jsonify({"password": os.getenv("SECRET_KEY")}), 200
    except Exception:
        import os as _os
        return jsonify({"password": _os.getenv("SECRET_KEY")}), 200

@admin_bp.route("/admin/password", methods=["POST"])
def update_password():
    import os
    data = request.get_json(silent=True) or {}
    current_key = data.get("admin_key", "").strip()
    new_password = data.get("new_password", "").strip()
    master = os.getenv("SECRET_KEY")
    stored = master
    try:
        doc = db.collection("settings").document("admin").get()
        if doc.exists:
            stored = doc.to_dict().get("password", master)
    except Exception:
        pass
    if current_key != stored and current_key != master:
        return jsonify({"error": "Incorrect current password."}), 401
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    try:
        db.collection("settings").document("admin").set({"password": new_password})
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
