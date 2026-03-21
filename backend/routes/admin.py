from flask import Blueprint, request, jsonify
from services.database import (
    get_all_entries,
    add_entry,
    update_entry,
    delete_entry,
    get_chat_logs,
    get_topic_stats
)

admin_bp = Blueprint("admin", __name__)


# ── Protect all admin routes with a simple secret key ────────
def check_admin_key():
    """
    Simple admin authentication.
    Frontend must send: { "admin_key": "your-secret-key" }
    """
    data = request.get_json(silent=True) or {}
    key = data.get("admin_key") or request.headers.get("X-Admin-Key") or request.args.get("admin_key")
    import os
    return key == os.getenv("SECRET_KEY")


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
        return jsonify({
            "total_questions": total,
            "by_topic": topic_stats
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── File Upload & AI Extraction ───────────────────────────────
@admin_bp.route("/admin/upload", methods=["POST"])
def upload_file():
    """Upload a PDF or TXT file and extract Q&A pairs using Gemini."""
    data = request.get_json(silent=True) or {}
    key = data.get("admin_key") or request.headers.get("X-Admin-Key") or request.args.get("admin_key")
    import os
    if key != os.getenv("SECRET_KEY"):
        return jsonify({"error": "Unauthorized"}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = file.filename.lower()
    text = ""

    try:
        if filename.endswith(".txt"):
            text = file.read().decode("utf-8", errors="ignore")
        elif filename.endswith(".docx"):
            from docx import Document
            import io
            doc = Document(io.BytesIO(file.read()))
            text = "\n".join([p.text for p in doc.paragraphs])
        elif filename.endswith(".pdf"):
            import PyPDF2, io
            reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            for page in reader.pages:
                text += page.extract_text() or ""
        else:
            return jsonify({"error": "Only PDF, TXT and DOCX files are supported"}), 400

        if not text.strip():
            return jsonify({"error": "Could not extract text from file"}), 400

        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        prompt = f"""You are a knowledge base builder for a university student assistant chatbot.

Read the following document and extract 5 to 15 useful Q&A pairs that students would ask.

Return ONLY a valid JSON array. No explanation. No markdown. Just the array.

Format:
[
  {{
    "topic": "one of: fees, registration, exams, hostel, enrollment, general",
    "question": "question a student would ask",
    "answer": "clear direct answer from the document",
    "keywords": "comma separated keywords"
  }}
]

Document:
{text[:8000]}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        import json
        entries = json.loads(raw)
        return jsonify({"entries": entries, "count": len(entries)}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
