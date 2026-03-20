import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ── Initialize Firebase ──────────────────────────────────────
cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


# ── Knowledge Base ───────────────────────────────────────────
def get_knowledge_base():
    """Fetch all active knowledge base entries from Firebase."""
    docs = db.collection("knowledge_base") \
             .where("active", "==", True) \
             .stream()
    return [doc.to_dict() for doc in docs]


def get_knowledge_base_by_topic(topic):
    """Fetch entries for a specific topic only."""
    docs = db.collection("knowledge_base") \
             .where("topic", "==", topic) \
             .where("active", "==", True) \
             .stream()
    return [doc.to_dict() for doc in docs]


# ── Chat Logging ─────────────────────────────────────────────
def log_chat(question, answer, topic=None):
    """Save every student question and answer for admin analytics."""
    db.collection("chat_logs").add({
        "question": question,
        "answer": answer,
        "topic": topic or "general",
        "timestamp": firestore.SERVER_TIMESTAMP
    })


# ── Admin — Read Entries ──────────────────────────────────────
def get_all_entries():
    """Fetch all knowledge base entries (including inactive) for admin panel."""
    docs = db.collection("knowledge_base").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


# ── Admin — Add Entry ─────────────────────────────────────────
def add_entry(topic, question, answer, keywords=""):
    """Add a new knowledge base entry from the admin panel."""
    doc_ref = db.collection("knowledge_base").add({
        "topic": topic,
        "question": question,
        "answer": answer,
        "keywords": keywords,
        "active": True,
        "source": "admin"
    })
    return doc_ref[1].id


# ── Admin — Update Entry ──────────────────────────────────────
def update_entry(entry_id, data):
    """Update an existing knowledge base entry."""
    db.collection("knowledge_base").document(entry_id).update(data)


# ── Admin — Delete Entry ──────────────────────────────────────
def delete_entry(entry_id):
    """Soft delete — sets active to False instead of removing."""
    db.collection("knowledge_base").document(entry_id).update({
        "active": False
    })


# ── Admin — Analytics ─────────────────────────────────────────
def get_chat_logs(limit=50):
    """Fetch recent chat logs for the admin analytics dashboard."""
    docs = db.collection("chat_logs") \
             .order_by("timestamp", direction=firestore.Query.DESCENDING) \
             .limit(limit) \
             .stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_topic_stats():
    """Count how many questions have been asked per topic."""
    docs = db.collection("chat_logs").stream()
    stats = {}
    for doc in docs:
        topic = doc.to_dict().get("topic", "general")
        stats[topic] = stats.get(topic, 0) + 1
    return stats