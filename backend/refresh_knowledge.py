"""
refresh_knowledge.py
=====================
Scrapes all official ACity URLs, uses Gemini to extract Q&A pairs
from each page, and saves them into Firestore intelligently:

  source = "auto_refresh"          → replaced every run (live info)
  source = "admin" / "initial_upload" → never touched
  permanent = True (any source)    → never touched, ever

HOW TO RUN:
    cd backend
    python refresh_knowledge.py

WHEN TO RUN:
    - Start of each semester
    - When fees or programmes change
    - Any time the ACity website is updated
"""

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()


# ── URLs to scrape ────────────────────────────────────────────
URLS = [
    # Core university info
    ("general",      "https://acity.edu.gh/"),
    ("general",      "https://acity.edu.gh/about/"),
    ("general",      "https://acity.edu.gh/about/executive-team/"),
    ("general",      "https://acity.edu.gh/about/governing-council/"),
    ("general",      "https://acity.edu.gh/the-acity-advantage/"),
    ("general",      "https://acity.edu.gh/contact-connect/"),
    ("general",      "https://acity.edu.gh/visit/"),
    ("general",      "https://acity.edu.gh/academic-city-staff-directory/"),
    ("general",      "https://acity.edu.gh/media-relations/"),
    ("general",      "https://acity.edu.gh/careers-at-acity/"),
    ("general",      "https://acity.edu.gh/virtual-tour/"),

    # Programmes
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/"),
    ("enrollment",   "https://acity.edu.gh/graduate-programmes/"),
    ("enrollment",   "https://acity.edu.gh/professional-certificate-programmes/"),

    # Admissions & registration
    ("registration", "https://acity.edu.gh/entry-requirements/"),
    ("registration", "https://acity.edu.gh/start-your-application/"),
    ("registration", "https://acity.edu.gh/registry/"),
    ("registration", "https://admissions.acity.edu.gh/undergraduate"),

    # Fees
    ("fees",         "https://acity.edu.gh/fees-scholarships/"),
    ("fees",         "https://acity.edu.gh/finance-billing/"),

    # Student life
    ("hostel",       "https://acity.edu.gh/student-life/"),
    ("hostel",       "https://acity.edu.gh/student-life/dining-meal-plans/"),
    ("general",      "https://acity.edu.gh/student-life/career-services/"),
    ("general",      "https://acity.edu.gh/student-corner/"),
    ("general",      "https://acity.edu.gh/student-app/"),

    # Academics & exams
    ("exams",        "https://acity.edu.gh/academic-resources/"),
    ("general",      "https://acity.edu.gh/library/"),

    # Foundation
    ("general",      "https://acityfoundation.org/"),
]

QA_PER_PAGE = 8


# ── Firebase setup ────────────────────────────────────────────
def init_firebase():
    firebase_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if firebase_json:
        cred = credentials.Certificate(json.loads(firebase_json))
    else:
        cred = credentials.Certificate("firebase-service-account.json")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ── Scrape a single URL ───────────────────────────────────────
def scrape_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (ACity Bot Knowledge Refresher)"}
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            print(f"  ⚠️  HTTP {r.status_code} — skipping {url}")
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        clean = " ".join(text.split())
        return clean[:6000]
    except Exception as e:
        print(f"  ❌ Failed to fetch {url}: {e}")
        return ""


# ── Ask Gemini to extract Q&A pairs from page content ─────────
def extract_qa_pairs(content, url, topic, client):
    if not content or len(content) < 100:
        return []

    prompt = f"""You are extracting knowledge base entries for an AI student assistant at Academic City University College (ACity) in Accra, Ghana.

From the page content below (scraped from {url}), extract up to {QA_PER_PAGE} clear, useful Q&A pairs that a student would actually ask.

RULES:
- Questions must be things a real student would ask
- Answers must come directly from the content — do not invent information
- Skip navigation text, cookie notices, and repeated footer content
- Skip vague marketing sentences with no concrete information
- Each answer should be 1–4 sentences, specific and factual
- Respond ONLY with a valid JSON array — no explanation, no markdown, no code fences

FORMAT (strict JSON array):
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]

PAGE CONTENT:
{content}"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_level="minimal")
            )
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        pairs = json.loads(raw)
        return pairs if isinstance(pairs, list) else []
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error for {url}: {e}")
        return []
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"  ⏳ Rate limited — waiting 30 seconds...")
            time.sleep(30)
            return []
        print(f"  ❌ Gemini error for {url}: {e}")
        return []


# ── Smart entry management ────────────────────────────────────
def clear_auto_refresh_entries(db):
    """
    Only removes entries where:
      - source == "auto_refresh"   AND
      - permanent != True

    This means:
      ✅ admin / initial_upload entries → always safe
      ✅ permanent=True entries        → always safe, regardless of source
      ♻️  auto_refresh non-permanent   → cleared and replaced
    """
    print("🧹 Clearing replaceable auto-refresh entries...")
    docs = (
        db.collection("knowledge_base")
          .where("source", "==", "auto_refresh")
          .stream()
    )
    removed = 0
    kept = 0
    for doc in docs:
        data = doc.to_dict()
        if data.get("permanent") is True:
            kept += 1  # marked permanent — never delete
        else:
            doc.reference.delete()
            removed += 1

    print(f"   Removed : {removed} old auto-refresh entries")
    print(f"   Kept    : {kept} permanent auto-refresh entries\n")


def save_to_firestore(db, topic, pairs, url):
    """
    Saves new Q&A pairs to Firestore.
    Skips near-duplicate questions already in the KB
    (compares lowercased first 60 chars of question).
    """
    # Load existing questions for duplicate check (once per call)
    existing_qs = set()
    existing_docs = db.collection("knowledge_base").where("active", "==", True).stream()
    for doc in existing_docs:
        q = doc.to_dict().get("question", "")
        existing_qs.add(q.lower()[:60])

    saved = 0
    skipped = 0
    for pair in pairs:
        q = pair.get("question", "").strip()
        a = pair.get("answer", "").strip()
        if not q or not a or len(q) < 10 or len(a) < 10:
            continue

        # Skip if a very similar question already exists
        if q.lower()[:60] in existing_qs:
            skipped += 1
            continue

        try:
            db.collection("knowledge_base").add({
                "topic":        topic,
                "question":     q,
                "answer":       a,
                "keywords":     "",
                "active":       True,
                "source":       "auto_refresh",
                "permanent":    False,   # set to True in Admin Panel to protect an entry
                "url":          url,
                "refreshed_at": firestore.SERVER_TIMESTAMP
            })
            existing_qs.add(q.lower()[:60])  # prevent duplicates within same run
            saved += 1
        except Exception as e:
            print(f"  ❌ Firestore save error: {e}")

    if skipped:
        print(f"   ⏭️  Skipped {skipped} duplicate questions")
    return saved


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  ACity Knowledge Base — Auto Refresh Tool")
    print("=" * 60)
    print(f"  URLs to process : {len(URLS)}")
    print(f"  Q&A per page    : {QA_PER_PAGE}")
    print(f"  Max new entries : ~{len(URLS) * QA_PER_PAGE}")
    print()
    print("  ENTRY PROTECTION RULES:")
    print("  ✅ source=admin / initial_upload → never touched")
    print("  ✅ permanent=True (any source)   → never touched")
    print("  ♻️  source=auto_refresh          → replaced")
    print("=" * 60)

    api_key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ No GEMINI_API_KEY found in .env — aborting.")
        return

    print()
    confirm = input("Proceed with refresh? [y/n]: ")
    if confirm.lower() != "y":
        print("Cancelled.")
        return

    db = init_firebase()
    client = genai.Client(api_key=api_key)

    clear_auto_refresh_entries(db)

    total_saved = 0
    total_failed = 0

    for i, (topic, url) in enumerate(URLS, 1):
        print(f"[{i}/{len(URLS)}] {url}")
        content = scrape_url(url)
        if not content:
            total_failed += 1
            continue

        print(f"   📄 {len(content)} chars — extracting Q&A pairs...")
        pairs = extract_qa_pairs(content, url, topic, client)
        if not pairs:
            print(f"   ⚠️  No Q&A pairs extracted.")
            total_failed += 1
            continue

        saved = save_to_firestore(db, topic, pairs, url)
        total_saved += saved
        print(f"   ✅ Saved {saved} new entries (topic: {topic})")
        time.sleep(2)  # avoid rate limits

    print()
    print("=" * 60)
    print(f"  ✅ Refresh complete!")
    print(f"  New entries saved  : {total_saved}")
    print(f"  Pages failed       : {total_failed}")
    print(f"  Protected entries  : untouched")
    print("=" * 60)
    print()
    print("Your bot now uses the updated knowledge base immediately.")
    print("Tip: In the Admin Panel, set permanent=True on any entry")
    print("     you never want auto-refresh to remove.")


if __name__ == "__main__":
    main()
