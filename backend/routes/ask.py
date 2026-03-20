from flask import Blueprint, request, jsonify
from services.gemini_service import get_ai_response
from services.database import get_knowledge_base, log_chat

ask_bp = Blueprint("ask", __name__)


@ask_bp.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()

        if not data or "question" not in data:
            return jsonify({"error": "Please provide a question."}), 400

        question = data["question"].strip()
        history = data.get("history", [])  # conversation history from frontend

        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400

        if len(question) > 500:
            return jsonify({"error": "Question is too long."}), 400

        knowledge_base = get_knowledge_base()
        answer = get_ai_response(question, knowledge_base, history)
        topic = detect_topic(question)
        log_chat(question, answer, topic)

        return jsonify({"answer": answer, "topic": topic}), 200

    except Exception as e:
        print(f"Error in /ask endpoint: {e}")
        return jsonify({
            "answer": "Sorry, I'm having trouble right now. Please try again or contact the Registry at registry@acity.edu.gh.",
            "topic": "error"
        }), 500


def detect_topic(question):
    q = question.lower()
    if any(w in q for w in ["fee", "pay", "cost", "ghs", "usd", "scholarship"]):
        return "fees"
    if any(w in q for w in ["register", "registration", "portal", "cohort"]):
        return "registration"
    if any(w in q for w in ["enroll", "course", "timetable", "programme", "major", "change course"]):
        return "enrollment"
    if any(w in q for w in ["exam", "result", "grade", "resit", "graduation"]):
        return "exams"
    if any(w in q for w in ["hostel", "accommodation", "room", "housing"]):
        return "hostel"
    return "general"
