import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ── Initialize PRIMARY database (your existing one) ───────────
firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
if firebase_json:
    cred1 = credentials.Certificate(json.loads(firebase_json))
else:
    cred1 = credentials.Certificate("firebase-service-account.json")

firebase_admin.initialize_app(cred1)
db = firestore.client()  # keeps working exactly as before

# ── Initialize SECONDARY database (new one) ───────────────────
firebase_json_2 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON_2")
db2 = None  # starts as None — only connects if the key exists

if firebase_json_2:
    try:
        cred2 = credentials.Certificate(json.loads(firebase_json_2))
        app2 = firebase_admin.initialize_app(cred2, name="secondary_db")
        db2 = firestore.client(app=app2)
        print("✅ Secondary Firebase connected.")
    except Exception as e:
        print(f"⚠️ Secondary Firebase failed to connect: {e}")


# ── Smart save: tries DB1 first, falls back to DB2 ───────────
def smart_add(collection_name, data):
    try:
        db.collection(collection_name).add(data)
    except Exception:
        if db2:
            db2.collection(collection_name).add(data)
        else:
            raise


# ── All your existing functions stay the same ─────────────────
def get_knowledge_base():
    results = []
    for database in [db, db2]:
        if database:
            docs = database.collection("knowledge_base").where("active", "==", True).stream()
            results.extend([doc.to_dict() for doc in docs])
    return results

def get_knowledge_base_by_topic(topic):
    results = []
    for database in [db, db2]:
        if database:
            docs = database.collection("knowledge_base").where("topic", "==", topic).where("active", "==", True).stream()
            results.extend([doc.to_dict() for doc in docs])
    return results

def log_chat(question, answer, topic=None):
    smart_add("chat_logs", {
        "question": question,
        "answer": answer,
        "topic": topic or "general",
        "timestamp": firestore.SERVER_TIMESTAMP
    })

def get_all_entries():
    results = []
    for database in [db, db2]:
        if database:
            docs = database.collection("knowledge_base").stream()
            results.extend([{"id": doc.id, **doc.to_dict()} for doc in docs])
    return results

def add_entry(topic, question, answer, keywords=""):
    data = {
        "topic": topic,
        "question": question,
        "answer": answer,
        "keywords": keywords,
        "active": True,
        "source": "admin"
    }
    smart_add("knowledge_base", data)
    return "added"

def update_entry(entry_id, data):
    try:
        db.collection("knowledge_base").document(entry_id).update(data)
    except Exception:
        if db2:
            db2.collection("knowledge_base").document(entry_id).update(data)

def delete_entry(entry_id):
    try:
        db.collection("knowledge_base").document(entry_id).update({"active": False})
    except Exception:
        if db2:
            db2.collection("knowledge_base").document(entry_id).update({"active": False})

def get_chat_logs(limit=50):
    docs = db.collection("chat_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

def get_topic_stats():
    stats = {}
    for database in [db, db2]:
        if database:
            docs = database.collection("chat_logs").stream()
            for doc in docs:
                topic = doc.to_dict().get("topic", "general")
                stats[topic] = stats.get(topic, 0) + 1
    return stats
