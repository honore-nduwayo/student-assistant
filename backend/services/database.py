"""
database.py
=======================
Single-database version — connects to one Firebase project only.

CACHE DURATION OPTIONS — change KB_CACHE_TTL to adjust:
  7200   ->  2 hours ->  88% reduction ->  6,000 reads/day  (conservative)
  21600  ->  6 hours ->  96% reduction ->  2,000 reads/day  RECOMMENDED
  43200  -> 12 hours ->  98% reduction ->  1,000 reads/day  (very stable KBs)
"""

import os
import json
import time
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ── CONFIGURATION ─────────────────────────────────────────────
KB_CACHE_TTL = 21600  # seconds — 6 hours recommended


# ── DATABASE CONNECTION ───────────────────────────────────────
firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
if firebase_json:
    cred = credentials.Certificate(json.loads(firebase_json))
else:
    cred = credentials.Certificate("firebase-service-account.json")

firebase_admin.initialize_app(cred)
db = firestore.client()


# ── IN-MEMORY CACHE ───────────────────────────────────────────
_kb_cache = None
_kb_cache_timestamp = 0.0


def _cache_is_stale():
    return _kb_cache is None or (time.time() - _kb_cache_timestamp) > KB_CACHE_TTL


def _invalidate_cache():
    global _kb_cache, _kb_cache_timestamp
    _kb_cache = None
    _kb_cache_timestamp = 0.0


# ── READS ─────────────────────────────────────────────────────
def get_knowledge_base():
    """Cached. Hits Firestore only on first call or after TTL expires."""
    global _kb_cache, _kb_cache_timestamp
    if _cache_is_stale():
        docs = (
            db.collection("knowledge_base")
            .where("active", "==", True)
            .stream()
        )
        _kb_cache = [doc.to_dict() for doc in docs]
        _kb_cache_timestamp = time.time()
    return _kb_cache


def get_knowledge_base_by_topic(topic):
    """Filters in-memory cache — zero Firestore reads."""
    return [e for e in get_knowledge_base() if e.get("topic") == topic]


def get_all_entries():
    """Admin panel only — bypasses cache so edits are visible immediately."""
    docs = db.collection("knowledge_base").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_chat_logs(limit=50):
    docs = (
        db.collection("chat_logs")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


def get_topic_stats():
    stats = {}
    for doc in db.collection("chat_logs").stream():
        topic = doc.to_dict().get("topic", "general")
        stats[topic] = stats.get(topic, 0) + 1
    return stats


# ── WRITES (always invalidate cache after) ────────────────────
def add_entry(topic, question, answer, keywords=""):
    db.collection("knowledge_base").add({
        "topic": topic,
        "question": question,
        "answer": answer,
        "keywords": keywords,
        "active": True,
        "source": "admin",
    })
    _invalidate_cache()
    return "added"


def update_entry(entry_id, data):
    db.collection("knowledge_base").document(entry_id).update(data)
    _invalidate_cache()


def delete_entry(entry_id):
    db.collection("knowledge_base").document(entry_id).update({"active": False})
    _invalidate_cache()


def log_chat(question, answer, topic=None):
    db.collection("chat_logs").add({
        "question": question,
        "answer": answer,
        "topic": topic or "general",
        "timestamp": firestore.SERVER_TIMESTAMP,
    })


# ── ADMIN CACHE HELPERS ───────────────────────────────────────
def force_refresh_cache():
    _invalidate_cache()
    return get_knowledge_base()


def get_cache_status():
    age = int(time.time() - _kb_cache_timestamp) if _kb_cache_timestamp else 0
    return {
        "cached": _kb_cache is not None,
        "entries": len(_kb_cache) if _kb_cache else 0,
        "age_seconds": age,
        "ttl_seconds": KB_CACHE_TTL,
        "expires_in_seconds": max(0, KB_CACHE_TTL - age),
    }
