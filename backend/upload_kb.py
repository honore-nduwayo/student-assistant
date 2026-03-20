"""
upload_kb.py
=============
One-time script to upload your qa_data.json knowledge base
into Firebase Firestore.

Run this ONCE to populate the database before launching the app.
You can also re-run it to refresh all entries — it clears the
old ones first so there are no duplicates.

Usage:
    python upload_kb.py
"""

import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()


# ── Connect to Firebase ───────────────────────────────────────
def init_firebase():
    cred = credentials.Certificate("firebase-service-account.json")
    firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Clear existing entries ────────────────────────────────────
def clear_existing(db):
    print("Clearing existing knowledge base entries...")
    docs = db.collection("knowledge_base").stream()
    count = 0
    for doc in docs:
        doc.reference.delete()
        count += 1
    print(f"Deleted {count} existing entries.")


# ── Upload new entries ────────────────────────────────────────
def upload_entries(db, entries):
    print(f"Uploading {len(entries)} entries to Firebase...")
    success = 0
    failed = 0

    for i, entry in enumerate(entries):
        try:
            db.collection("knowledge_base").add({
                "topic":    entry["topic"],
                "question": entry["question"],
                "answer":   entry["answer"],
                "keywords": entry.get("keywords", ""),
                "active":   True,
                "source":   "initial_upload"
            })
            success += 1

            # Show progress every 10 entries
            if (i + 1) % 10 == 0:
                print(f"  Uploaded {i + 1}/{len(entries)}...")

        except Exception as e:
            print(f"  Failed on entry {i + 1}: {e}")
            failed += 1

    return success, failed


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  ACity Knowledge Base Upload Tool")
    print("=" * 50)

    # Load the JSON file
    kb_path = os.path.join(
        os.path.dirname(__file__),
        "..", "knowledge-base", "qa_data.json"
    )

    if not os.path.exists(kb_path):
        print(f"Error: qa_data.json not found at {kb_path}")
        print("Make sure qa_data.json is in the knowledge-base/ folder.")
        return

    with open(kb_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    print(f"Loaded {len(entries)} entries from qa_data.json")

    # Count by topic
    topics = {}
    for e in entries:
        t = e["topic"]
        topics[t] = topics.get(t, 0) + 1

    print("\nEntries by topic:")
    for topic, count in sorted(topics.items()):
        print(f"  {topic}: {count}")

    # Confirm before uploading
    print()
    confirm = input("Proceed with upload? This will clear existing entries. [y/n]: ")
    if confirm.lower() != "y":
        print("Upload cancelled.")
        return

    # Connect and upload
    db = init_firebase()
    clear_existing(db)
    success, failed = upload_entries(db, entries)

    # Summary
    print()
    print("=" * 50)
    print(f"  Upload complete!")
    print(f"  Successful: {success}")
    print(f"  Failed:     {failed}")
    print(f"  Total in Firebase: {success}")
    print("=" * 50)


if __name__ == "__main__":
    main()