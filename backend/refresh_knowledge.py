"""
refresh_knowledge.py
=====================
Scrapes ALL official ACity URLs (including auto-discovered sublinks),
uses Gemini to extract Q&A pairs, and saves them to Firestore.

ENTRY PROTECTION:
  source = "admin" / "initial_upload" → never touched
  source = "auto_refresh", permanent=True  → never touched
  source = "auto_refresh", permanent=False → replaced each run

HOW TO RUN:
    cd backend
    python refresh_knowledge.py
"""

import os
import json
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()


# ── All URLs you provided ─────────────────────────────────────
SEED_URLS = [
    # ── Main site ─────────────────────────────────────────────
    ("general",      "https://acity.edu.gh/"),
    ("general",      "https://acity.edu.gh/about/"),
    ("general",      "https://acity.edu.gh/about/#accreditation"),
    ("general",      "https://acity.edu.gh/about/#global_partners"),
    ("general",      "https://acity.edu.gh/about/#our-history"),
    ("general",      "https://acity.edu.gh/about/#university-leadership"),
    ("general",      "https://acity.edu.gh/about/#vision_and_mission"),
    ("general",      "https://acity.edu.gh/about/executive-team/"),
    ("general",      "https://acity.edu.gh/about/governing-council/"),
    ("general",      "https://acity.edu.gh/academic-city-staff-directory/"),
    ("general",      "https://acity.edu.gh/academic-city-supports-digital-learning-with-donation-to-ga-east-schools/"),
    ("general",      "https://acity.edu.gh/academic-citys-tech-expo-showcases-innovative-technologies-to-tackle-galamsey/"),
    ("exams",        "https://acity.edu.gh/academic-resources/"),
    ("general",      "https://acity.edu.gh/author/blogeditor/"),
    ("general",      "https://acity.edu.gh/blog/"),
    ("general",      "https://acity.edu.gh/careers-at-acity/"),
    ("general",      "https://acity.edu.gh/category/acity-collaborates/"),
    ("general",      "https://acity.edu.gh/category/acity-community-engagement/"),
    ("general",      "https://acity.edu.gh/category/acity-innovates/"),
    ("general",      "https://acity.edu.gh/category/acity-shine/"),
    ("general",      "https://acity.edu.gh/contact-connect/"),
    ("registration", "https://acity.edu.gh/entry-requirements/"),
    ("fees",         "https://acity.edu.gh/fees-scholarships/"),
    ("fees",         "https://acity.edu.gh/finance-billing/"),
    ("enrollment",   "https://acity.edu.gh/graduate-programmes/"),
    ("enrollment",   "https://acity.edu.gh/graduate-programmes/#graduate-programmes"),
    ("general",      "https://acity.edu.gh/library/"),
    ("general",      "https://acity.edu.gh/media-relations/"),
    ("general",      "https://acity.edu.gh/privacy-policy/"),
    ("general",      "https://acity.edu.gh/prof-mcbagonluri-named-among-africas-top-education-leaders/"),
    ("enrollment",   "https://acity.edu.gh/professional-certificate-programmes/"),
    ("registration", "https://acity.edu.gh/registry/"),
    ("general",      "https://acity.edu.gh/staff-corner/"),
    ("registration", "https://acity.edu.gh/start-your-application/"),
    ("general",      "https://acity.edu.gh/strengthening-global-ties-academic-city-engages-ambassadors-of-japan-korea-and-mozambique/"),
    ("general",      "https://acity.edu.gh/student-app/"),
    ("general",      "https://acity.edu.gh/student-corner/"),
    ("hostel",       "https://acity.edu.gh/student-life/"),
    ("hostel",       "https://acity.edu.gh/student-life/#academic_city_student_council"),
    ("hostel",       "https://acity.edu.gh/student-life/#aclife"),
    ("hostel",       "https://acity.edu.gh/student-life/#clubs_at_acity"),
    ("hostel",       "https://acity.edu.gh/student-life/#health_&_wellness"),
    ("hostel",       "https://acity.edu.gh/student-life/#sports_and_recreation"),
    ("hostel",       "https://acity.edu.gh/student-life/#student_commitment"),
    ("general",      "https://acity.edu.gh/student-life/career-services/"),
    ("hostel",       "https://acity.edu.gh/student-life/dining-meal-plans/"),
    ("general",      "https://acity.edu.gh/the-acity-advantage/"),
    ("general",      "https://acity.edu.gh/the-exponent-acity-newsletter/"),
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/"),
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/#business"),
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/#communication-arts"),
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering"),
    ("enrollment",   "https://acity.edu.gh/undergraduate-programmes/#informatics"),
    ("general",      "https://acity.edu.gh/virtual-tour/"),
    ("general",      "https://acity.edu.gh/visit/"),

    # ── Sub-sites ─────────────────────────────────────────────
    ("general",      "https://acityfoundation.org/"),
    ("registration", "https://admissions.acity.edu.gh/undergraduate"),
]

ALLOWED_DOMAINS = {
    "acity.edu.gh",
    "acityfoundation.org",
    "admissions.acity.edu.gh",
    "acityplus.acity.edu.gh",
}

SKIP_PATTERNS = [
    "twitter.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "x.com",
    "login", "logout", "signin", "signup",
    "wp-admin", "wp-json", "feed", "xmlrpc",
    ".pdf", ".docx", ".xlsx", ".zip",
]

QA_PER_PAGE = 8
MAX_SUBLINKS_PER_PAGE = 5
MAX_TOTAL_URLS = 120

# ── Model to use for knowledge extraction ────────────────────
# gemini-3.1-flash-lite-preview: fastest, cheapest, great for bulk extraction
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")


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


# ── URL helpers ───────────────────────────────────────────────
def should_skip(url):
    return any(p in url.lower() for p in SKIP_PATTERNS)

def is_allowed_domain(url):
    try:
        domain = urlparse(url).netloc
        return any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS)
    except Exception:
        return False

def normalize_url(url):
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


# ── Scrape a page and return (text, discovered_sublinks) ──────
def scrape_url(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (ACity Bot Knowledge Refresher)"}
        r = requests.get(url, timeout=10, headers=headers)
        if r.status_code != 200:
            print(f"  ⚠️  HTTP {r.status_code} — skipping")
            return "", []

        soup = BeautifulSoup(r.text, "html.parser")

        sublinks = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].strip()
            full = urljoin(url, href)
            norm = normalize_url(full)
            if (
                is_allowed_domain(norm)
                and not should_skip(norm)
                and norm.startswith("http")
            ):
                sublinks.append(norm)

        for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        clean = " ".join(text.split())[:6000]

        return clean, list(dict.fromkeys(sublinks))

    except Exception as e:
        print(f"  ❌ Fetch error: {e}")
        return "", []


# ── Ask Gemini to extract Q&A pairs ───────────────────────────
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
            model=GEMINI_MODEL,
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
        print(f"  ⚠️  JSON parse error: {e}")
        return []
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"  ⏳ Rate limited — waiting 30 seconds...")
            time.sleep(30)
            return []
        print(f"  ❌ Gemini error: {e}")
        return []


# ── Smart Firestore management ────────────────────────────────
def clear_auto_refresh_entries(db):
    print("🧹 Clearing replaceable auto-refresh entries...")
    docs = db.collection("knowledge_base").where("source", "==", "auto_refresh").stream()
    removed = kept = 0
    for doc in docs:
        if doc.to_dict().get("permanent") is True:
            kept += 1
        else:
            doc.reference.delete()
            removed += 1
    print(f"   Removed : {removed}   |   Kept (permanent) : {kept}\n")


def save_to_firestore(db, topic, pairs, url, existing_qs):
    saved = skipped = 0
    for pair in pairs:
        q = pair.get("question", "").strip()
        a = pair.get("answer", "").strip()
        if not q or not a or len(q) < 10 or len(a) < 10:
            continue
        fingerprint = q.lower()[:60]
        if fingerprint in existing_qs:
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
                "permanent":    False,
                "url":          url,
                "refreshed_at": firestore.SERVER_TIMESTAMP
            })
            existing_qs.add(fingerprint)
            saved += 1
        except Exception as e:
            print(f"  ❌ Firestore save error: {e}")
    if skipped:
        print(f"   ⏭️  Skipped {skipped} duplicates")
    return saved


# ── Build full URL queue ──────────────────────────────────────
def build_url_queue(seed_urls):
    seen_pages = set()
    queue = []

    for topic, url in seed_urls:
        norm = normalize_url(url)
        if norm not in seen_pages and not should_skip(url):
            seen_pages.add(norm)
            queue.append((topic, url, True))

    print(f"   Seed URLs loaded     : {len(queue)}")
    print(f"   Now discovering sublinks on each seed page...\n")

    discovered = []
    for topic, url, _ in queue[:]:
        if len(queue) + len(discovered) >= MAX_TOTAL_URLS:
            break
        _, sublinks = scrape_url(url)
        added = 0
        for sub in sublinks:
            norm_sub = normalize_url(sub)
            if norm_sub not in seen_pages and len(discovered) + len(queue) < MAX_TOTAL_URLS:
                seen_pages.add(norm_sub)
                discovered.append((topic, sub, False))
                added += 1
                if added >= MAX_SUBLINKS_PER_PAGE:
                    break

    queue.extend(discovered)
    print(f"   Sublinks discovered  : {len(discovered)}")
    print(f"   Total URLs to scrape : {len(queue)}\n")
    return queue


# ── Main ──────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  ACity Knowledge Base — Auto Refresh Tool")
    print("=" * 60)
    print(f"  Seed URLs           : {len(SEED_URLS)}")
    print(f"  Max sublinks/page   : {MAX_SUBLINKS_PER_PAGE}")
    print(f"  Hard URL cap        : {MAX_TOTAL_URLS}")
    print(f"  Q&A per page        : {QA_PER_PAGE}")
    print(f"  Gemini model        : {GEMINI_MODEL}")
    print()
    print("  PROTECTION RULES:")
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
    print()

    db = init_firebase()
    client = genai.Client(api_key=api_key)

    print("🔍 Building URL queue...")
    url_queue = build_url_queue(SEED_URLS)

    print("📚 Loading existing KB questions for duplicate check...")
    existing_qs = set()
    for doc in db.collection("knowledge_base").where("active", "==", True).stream():
        q = doc.to_dict().get("question", "")
        existing_qs.add(q.lower()[:60])
    print(f"   Found {len(existing_qs)} existing questions\n")

    clear_auto_refresh_entries(db)

    total_saved = total_failed = 0

    for i, (topic, url, is_seed) in enumerate(url_queue, 1):
        label = "SEED" if is_seed else "SUB "
        print(f"[{i}/{len(url_queue)}] [{label}] {url}")

        content, _ = scrape_url(url)
        if not content:
            total_failed += 1
            continue

        print(f"   📄 {len(content)} chars — extracting Q&A pairs...")
        pairs = extract_qa_pairs(content, url, topic, client)

        if not pairs:
            print(f"   ⚠️  No Q&A pairs extracted.")
            total_failed += 1
            continue

        saved = save_to_firestore(db, topic, pairs, url, existing_qs)
        total_saved += saved
        print(f"   ✅ Saved {saved} new entries (topic: {topic})")
        time.sleep(2)

    print()
    print("=" * 60)
    print(f"  ✅ Refresh complete!")
    print(f"  URLs processed     : {len(url_queue)}")
    print(f"  New entries saved  : {total_saved}")
    print(f"  Pages with no data : {total_failed}")
    print(f"  Protected entries  : untouched")
    print("=" * 60)
    print()
    print("Your bot now uses the updated knowledge base immediately.")
    print("Tip: In Firestore, set permanent=True on any auto-refresh")
    print("     entry you want to keep forever (e.g. historical facts).")


if __name__ == "__main__":
    main()
