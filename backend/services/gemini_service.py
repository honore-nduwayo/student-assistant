import os
import re
import time
import hashlib
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


# ── API Key Rotation ──────────────────────────────────────────
def get_api_keys():
    keys = []
    i = 1
    while True:
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if not key:
            break
        keys.append(key)
        i += 1
    single = os.getenv("GEMINI_API_KEY")
    if single and single not in keys:
        keys.append(single)
    return keys


# ── Key cooldown state (lives for the process lifetime) ───────
# No permanent dead keys — every key recovers after its cooldown.
# 429 / RESOURCE_EXHAUSTED  → 65-second rest
# PERMISSION / LOCATION     → 1-hour rest (might be regional, not permanent)
_key_cooldowns: dict = {}   # {index: cooldown_until_timestamp}

def _available_keys(keys):
    now = time.time()
    return [
        (i, k) for i, k in enumerate(keys)
        if _key_cooldowns.get(i, 0) <= now
    ]

def _cooldown(i, seconds=65):
    _key_cooldowns[i] = time.time() + seconds
    print(f"[Key Cooldown] Key {i+1} resting for {seconds}s")


# ── Response cache (5-min TTL) ────────────────────────────────
# Identical questions served from memory — zero API calls.
_response_cache: dict = {}
RESPONSE_CACHE_TTL = 300  # seconds

def _cache_key(q: str) -> str:
    return hashlib.md5(q.lower().strip().encode()).hexdigest()

def _get_cached(q: str):
    entry = _response_cache.get(_cache_key(q))
    if entry and (time.time() - entry["ts"]) < RESPONSE_CACHE_TTL:
        print("[Cache] HIT — serving cached response")
        return entry["v"]
    return None

def _set_cached(q: str, response: str):
    _response_cache[_cache_key(q)] = {"v": response, "ts": time.time()}


# ─────────────────────────────────────────────────────────────
# ACADEMIC CALENDAR — DYNAMIC (Firestore) WITH HARDCODED FALLBACK
# ─────────────────────────────────────────────────────────────

FALLBACK_CALENDAR = {
    "semester_1_start":      "2025-09-01",
    "semester_1_end":        "2025-12-20",
    "semester_2_start":      "2026-01-12",
    "semester_2_end":        "2026-05-10",
    "exam_1_start":          "2025-12-08",
    "exam_1_end":            "2025-12-20",
    "exam_2_start":          "2026-04-27",
    "exam_2_end":            "2026-05-10",
    "break_start":           "2025-12-21",
    "break_end":             "2026-01-11",
    "academic_year":         "2025–2026",
    "semester_2_label_end":  "May 10, 2026",
    "exam_2_label":          "April 27 – May 10, 2026",
}

CALENDAR_CACHE_TTL = 21600  # 6 hours
_calendar_cache: dict | None = None
_calendar_cache_ts: float = 0.0


def get_academic_calendar() -> dict:
    global _calendar_cache, _calendar_cache_ts
    now = time.time()
    if _calendar_cache and (now - _calendar_cache_ts) < CALENDAR_CACHE_TTL:
        return _calendar_cache
    try:
        from services.database import db
        doc = db.collection("settings").document("academic_calendar").get()
        if doc.exists:
            data = doc.to_dict()
            required = [
                "semester_1_start", "semester_1_end",
                "semester_2_start", "semester_2_end",
                "exam_1_start",     "exam_1_end",
                "exam_2_start",     "exam_2_end",
                "break_start",      "break_end",
            ]
            if all(k in data for k in required):
                _calendar_cache = data
                _calendar_cache_ts = now
                return _calendar_cache
    except Exception as e:
        print(f"[Calendar] Firestore error ({e}) — using fallback")
    _calendar_cache = FALLBACK_CALENDAR
    _calendar_cache_ts = now
    return _calendar_cache


def _detect_current_period(now: datetime, cal: dict) -> str:
    today = now.date()

    def in_range(start_key, end_key):
        try:
            s = datetime.strptime(cal[start_key], "%Y-%m-%d").date()
            e = datetime.strptime(cal[end_key],   "%Y-%m-%d").date()
            return s <= today <= e
        except Exception:
            return False

    if in_range("exam_1_start",     "exam_1_end"):     return "Semester 1 Exams"
    if in_range("exam_2_start",     "exam_2_end"):     return "Semester 2 Exams"
    if in_range("semester_1_start", "semester_1_end"): return "Semester 1 (classes)"
    if in_range("semester_2_start", "semester_2_end"): return "Semester 2 (classes)"
    if in_range("break_start",      "break_end"):      return "Semester Break"
    return "Pre-semester / Registration"


# ─────────────────────────────────────────────────────────────
# KEYWORD → URL MAP
# ─────────────────────────────────────────────────────────────

KEYWORD_URL_MAP = [
    {"label": "about_general", "keywords": ["about", "what is acity", "academic city", "overview", "who is", "tell me about", "acity university", "advantage", "why acity", "unique", "special"], "urls": ["https://acity.edu.gh/", "https://acity.edu.gh/about/", "https://acity.edu.gh/the-acity-advantage/"]},
    {"label": "history", "keywords": ["history", "founded", "established", "origin", "when was", "how old", "started", "creation"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#our-history"]},
    {"label": "vision_mission", "keywords": ["vision", "mission", "values", "goals", "purpose", "philosophy", "objective"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#vision_and_mission"]},
    {"label": "accreditation", "keywords": ["accredited", "accreditation", "nab", "recognized", "approved", "legitimate", "certified"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#accreditation"]},
    {"label": "global_partners", "keywords": ["partners", "partnerships", "international", "global", "collaboration", "mou", "exchange"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#global_partners"]},
    {"label": "leadership", "keywords": ["leadership", "vice chancellor", "vc", "president", "rector", "management", "executive", "governing council", "who leads", "administration", "head", "chancellor", "mcbagonluri", "provost", "dean"], "urls": ["https://acity.edu.gh/about/#university-leadership", "https://acity.edu.gh/about/executive-team/", "https://acity.edu.gh/about/governing-council/"]},
    {"label": "contact", "keywords": ["contact", "phone", "email", "reach", "call", "whatsapp", "helpdesk", "support", "inquire", "get in touch"], "urls": ["https://acity.edu.gh/contact-connect/", "https://acity.edu.gh/registry/"]},
    {"label": "location_visit", "keywords": ["location", "where is", "address", "campus", "directions", "map", "how to get", "visit", "find acity", "east legon", "accra", "haatso"], "urls": ["https://acity.edu.gh/visit/", "https://acity.edu.gh/contact-connect/"]},
    {"label": "student_app", "keywords": ["student app", "acity app", "acityplus", "acity+", "mobile app", "portal app", "student portal", "login portal"], "urls": ["https://acity.edu.gh/student-app/", "https://acityplus.acity.edu.gh/"]},
    {"label": "library", "keywords": ["library", "books", "journals", "research material", "database", "e-library", "borrow"], "urls": ["https://acity.edu.gh/library/", "https://acity.edu.gh/academic-resources/"]},
    {"label": "careers_jobs", "keywords": ["job", "jobs", "career", "vacancy", "vacancies", "employment", "work at acity", "hiring", "recruitment"], "urls": ["https://acity.edu.gh/careers-at-acity/"]},
    {"label": "undergraduate_all", "keywords": ["undergraduate", "bachelor", "bsc", "bba", "ba", "degree programme", "what programmes", "all programmes", "list of programmes", "available courses", "offered"], "urls": ["https://acity.edu.gh/undergraduate-programmes/"]},
    {"label": "engineering", "keywords": ["engineering", "computer engineering", "electrical engineering", "mechanical engineering", "biomedical engineering", "robotics engineering"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering"]},
    {"label": "informatics", "keywords": ["computer science", "cs", "information technology", "it", "artificial intelligence", "ai", "informatics", "software", "machine learning", "data science"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#informatics"]},
    {"label": "business", "keywords": ["business", "bba", "accounting", "marketing", "finance", "banking", "entrepreneurship", "management", "commerce"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#business"]},
    {"label": "communication_arts", "keywords": ["communication", "journalism", "mass communication", "advertising", "public relations", "pr", "media studies"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#communication-arts"]},
    {"label": "graduate", "keywords": ["graduate", "postgraduate", "masters", "msc", "mba", "phd", "graduate school", "msc cybersecurity", "msc data science"], "urls": ["https://acity.edu.gh/graduate-programmes/"]},
    {"label": "professional_certificate", "keywords": ["certificate", "professional certificate", "short course", "diploma", "cpd", "continuing education"], "urls": ["https://acity.edu.gh/professional-certificate-programmes/"]},
    {"label": "admissions_apply", "keywords": ["apply", "application", "how to apply", "admission", "apply online", "admissions portal", "entry requirements", "wassce", "sssce", "a levels", "eligibility", "freshman", "new student", "intake", "cohort"], "urls": ["https://acity.edu.gh/start-your-application/", "https://acity.edu.gh/entry-requirements/", "https://admissions.acity.edu.gh/undergraduate"]},
    {"label": "registry", "keywords": ["registry", "registrar", "student id", "matric number", "transcript", "clearance", "graduation clearance", "deferral", "verification letter", "academic records"], "urls": ["https://acity.edu.gh/registry/"]},
    {"label": "fees_tuition", "keywords": ["fee", "fees", "tuition", "cost", "how much", "price", "ghs", "usd", "cedis", "pay", "payment", "amount", "charges", "billing", "invoice", "receipt"], "urls": ["https://acity.edu.gh/fees-scholarships/", "https://acity.edu.gh/finance-billing/"]},
    {"label": "scholarships", "keywords": ["scholarship", "bursary", "financial aid", "grant", "discount", "free tuition", "sponsored", "merit award", "fellowship"], "urls": ["https://acity.edu.gh/fees-scholarships/"]},
    {"label": "finance_payment", "keywords": ["pay fees", "how to pay", "payment method", "bank transfer", "mobile money", "momo", "mtn momo", "finance office", "installment", "payment deadline"], "urls": ["https://acity.edu.gh/finance-billing/"]},
    {"label": "exams_results", "keywords": ["exam", "exams", "examination", "test", "quiz", "assessment", "result", "results", "grade", "grades", "gpa", "cgpa", "score", "transcript", "resit", "repeat exam", "supplementary", "pass", "fail", "check result"], "urls": ["https://acity.edu.gh/academic-resources/", "https://acityplus.acity.edu.gh/login", "https://acity.edu.gh/registry/"]},
    {"label": "academic_calendar", "keywords": ["academic calendar", "semester", "semester dates", "when does semester", "school calendar", "term dates", "vacation", "break", "holiday", "exam period", "exam timetable"], "urls": ["https://acity.edu.gh/academic-resources/"]},
    {"label": "graduation", "keywords": ["graduation", "convocation", "ceremony", "certificate collection", "graduation gown", "when is graduation", "graduation requirements", "complete my degree"], "urls": ["https://acity.edu.gh/registry/", "https://acity.edu.gh/academic-resources/"]},
    {"label": "hostel_accommodation", "keywords": ["hostel", "accommodation", "housing", "room", "dormitory", "dorm", "on campus", "residential", "stay on campus", "bed space", "live on campus", "aclife"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#aclife"]},
    {"label": "dining", "keywords": ["dining", "food", "canteen", "cafeteria", "meal plan", "lunch", "breakfast", "dinner", "eat on campus", "meal ticket"], "urls": ["https://acity.edu.gh/student-life/dining-meal-plans/"]},
    {"label": "health_wellness", "keywords": ["health", "wellness", "clinic", "doctor", "sick", "nurse", "mental health", "counseling", "hospital", "medical", "health center"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#health_&_wellness"]},
    {"label": "sports_recreation", "keywords": ["sports", "recreation", "gym", "football", "basketball", "tennis", "exercise", "fitness", "athletics", "games", "swimming", "volleyball"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#sports_and_recreation"]},
    {"label": "clubs_societies", "keywords": ["club", "clubs", "societies", "student activities", "extracurricular", "associations", "groups", "student organization", "join a club"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#clubs_at_acity"]},
    {"label": "student_council", "keywords": ["student council", "src", "acsc", "student government", "student union", "student representative", "student body", "student affairs"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#academic_city_student_council"]},
    {"label": "career_services", "keywords": ["career services", "internship", "job placement", "cv writing", "resume", "interview prep", "industry placement", "work experience", "career fair"], "urls": ["https://acity.edu.gh/student-life/career-services/"]},
    {"label": "enrollment_courses", "keywords": ["enroll", "enrollment", "add course", "drop course", "change course", "change major", "timetable", "class schedule", "course registration", "hod", "credit hours", "elective", "core course"], "urls": ["https://acity.edu.gh/academic-resources/", "https://acity.edu.gh/registry/", "https://acityplus.acity.edu.gh/"]},
]

SKIP_LIVE_FETCH = {
    "twitter.com", "x.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com",
}

MAX_LIVE_URLS = 2


def detect_live_urls(question: str) -> list:
    q = question.lower()
    scored = []
    for entry in KEYWORD_URL_MAP:
        score = sum(1 for kw in entry["keywords"] if kw in q)
        if score > 0:
            scored.append((score, entry["label"], entry["urls"]))
    if not scored:
        return ["https://acity.edu.gh/"]
    scored.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    result = []
    for score, label, urls in scored:
        for url in urls:
            domain = urlparse(url).netloc.replace("www.", "")
            if url not in seen and domain not in SKIP_LIVE_FETCH:
                seen.add(url)
                result.append(url)
                if len(result) >= MAX_LIVE_URLS:
                    print(f"[URL Router] label='{label}' score={score} → {result}")
                    return result
    return result or ["https://acity.edu.gh/"]


# ── Topic Detection ───────────────────────────────────────────
TOPIC_KEYWORDS = {
    "fees":         ["fee", "fees", "cost", "pay", "payment", "tuition", "amount", "price", "ghs", "cedis", "scholarship", "financial", "bursary", "receipt", "billing"],
    "registration": ["register", "registration", "admit", "admission", "apply", "application", "form", "portal", "login", "password", "student id", "matric", "entry requirement", "wassce"],
    "exams":        ["exam", "exams", "test", "quiz", "assessment", "result", "grade", "score", "gpa", "cgpa", "transcript", "resit", "repeat", "academic calendar", "semester", "timetable"],
    "hostel":       ["hostel", "accommodation", "room", "bed", "dorm", "dormitory", "residential", "housing", "live", "stay", "campus life", "dining", "meal"],
    "enrollment":   ["enroll", "enrollment", "course", "courses", "credit", "unit", "timetable", "schedule", "hod", "department", "programme", "major", "elective", "add", "drop", "computer science", "bsc", "bba", "ba", "engineering"],
}

def detect_topic(question: str) -> str:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


# ── Page scraper with 30-min cache ────────────────────────────
_page_cache: dict = {}
CACHE_TTL = 1800

def fetch_page_content(url: str) -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    if domain in SKIP_LIVE_FETCH:
        return ""
    now = time.time()
    if url in _page_cache:
        content, cached_at = _page_cache[url]
        if now - cached_at < CACHE_TTL:
            return content
    try:
        headers = {"User-Agent": "Mozilla/5.0 (ACity Student Bot)"}
        r = requests.get(url, timeout=6, headers=headers)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        content = " ".join(text.split())[:1500]
        _page_cache[url] = (content, now)
        return content
    except Exception:
        return ""


def fetch_live_content(question: str) -> str:
    urls = detect_live_urls(question)
    parts = []
    for url in urls:
        content = fetch_page_content(url)
        if content:
            parts.append(f"[{url}]\n{content}")
    return "\n\n".join(parts) if parts else ""


# ── Smart KB filter ───────────────────────────────────────────
def get_relevant_kb_entries(question: str, knowledge_base: list, topic: str, max_entries: int = 12) -> str:
    q = question.lower()

    stopwords = {"the", "a", "an", "is", "are", "was", "were", "do", "does",
                 "did", "i", "my", "me", "what", "when", "where", "how",
                 "can", "will", "please", "tell", "about", "for", "of", "to"}
    q_words = [w for w in re.findall(r'\b\w+\b', q) if len(w) > 2 and w not in stopwords]

    scored = []
    for entry in knowledge_base:
        if not entry.get("active", True):
            continue
        entry_text = (
            entry.get("question", "") + " " +
            entry.get("keywords", "") + " " +
            entry.get("answer", "")[:200]
        ).lower()
        score = sum(1 for word in q_words if word in entry_text)
        if entry.get("topic") == topic:
            score += 1
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [e for _, e in scored[:max_entries]]

    if not top:
        top = [
            e for e in knowledge_base
            if e.get("topic") == topic and e.get("active", True)
        ][:max_entries]

    result = ""
    for entry in top:
        result += f"Q: {entry.get('question', '').strip()}\nA: {entry.get('answer', '').strip()}\n\n"

    print(f"[KB Filter] Matched {len(top)} entries (topic: {topic}, query words: {q_words[:5]})")
    return result


# ── Real-Time Context ─────────────────────────────────────────
def get_dynamic_context() -> str:
    now      = datetime.now(ZoneInfo("Africa/Accra"))
    day_name = now.strftime("%A")
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%B %d, %Y")
    hour     = now.hour
    weekday  = now.weekday()

    is_office_hrs = (weekday < 5) and (8 <= hour < 17)
    office_status = "OPEN (Mon–Fri, 8 AM–5 PM GMT)" if is_office_hrs else "CLOSED"

    cal = get_academic_calendar()
    current_period = _detect_current_period(now, cal)
    academic_year  = cal.get("academic_year", FALLBACK_CALENDAR["academic_year"])
    sem2_end       = cal.get("semester_2_label_end", FALLBACK_CALENDAR["semester_2_label_end"])
    exam2_label    = cal.get("exam_2_label", FALLBACK_CALENDAR["exam_2_label"])

    return (
        f"DATE:{date_str} ({day_name}) | TIME:{time_str} GMT | "
        f"PERIOD:{current_period} | SEM2 ENDS:{sem2_end} | "
        f"EXAMS2:{exam2_label} | OFFICES:{office_status} | YEAR:{academic_year}"
    )


# ── Main AI Response Function ─────────────────────────────────
def get_ai_response(question: str, knowledge_base: list, history: list) -> str:

    # 1. Check response cache — identical questions cost zero API calls
    cached = _get_cached(question)
    if cached:
        return cached

    # 2. Detect topic
    topic = detect_topic(question)

    # 3. Smart KB filter — top 12 relevant entries only
    kb_text = get_relevant_kb_entries(question, knowledge_base, topic, max_entries=12)

    # 4. Fetch live page content
    live_content = fetch_live_content(question)

    # 5. Real-time context
    dynamic_context = get_dynamic_context()

    # 6. Last 6 messages of history
    history_text = ""
    for msg in history[-6:]:
        role = "Student" if msg.get("role") == "user" else "Kai"
        history_text += f"{role}: {msg.get('text', '')}\n"

    # 7. Prompt
    prompt = f"""You are Kai, the official AI student assistant for Academic City University College (ACity), Accra, Ghana. Be warm, clear, and concise.

CONTEXT: {dynamic_context}

FORMATTING RULES (never break these):
- NO markdown links. Write URLs plainly: "Visit: https://acity.edu.gh/registry/"
- Use numbered steps for any process (how to apply, how to pay, etc.)
- Use bullet points (•) for lists of facts
- Bold key terms with **bold**
- Keep answers concise — 1–2 sentences per point

ANSWER PRIORITY:
1. Use KNOWLEDGE BASE entries below if relevant — give the info directly
2. Use LIVE CONTENT if KB has nothing — extract the answer clearly
3. Use CONTEXT block for date/semester/office hour questions
4. Last resort: general knowledge + direct to registry@acity.edu.gh

HISTORY:
{history_text}

KNOWLEDGE BASE (topic: {topic}):
{kb_text}
LIVE CONTENT:
{live_content}

Question: {question}

End every response with:
"💬 Anything else I can help with? I'm Kai — always here for questions on fees, registration, courses, exams, hostels, and more!"

Answer:"""

    # 8. API key rotation with cooldown — only try available keys
    keys = get_api_keys()
    model = "gemini-3.1-flash-lite-preview"
    available = _available_keys(keys)

    print(f"[API Rotation] {len(available)}/{len(keys)} key(s) available — model: {model}")

    if not available:
        # All keys are on cooldown — tell the student how long to wait
        next_ready = min(_key_cooldowns.values(), default=time.time())
        wait_secs = max(1, int(next_ready - time.time()))
        print(f"[API Rotation] All keys on cooldown. Next ready in ~{wait_secs}s")
        return (
            f"I'm at capacity right now. Please try again in about {wait_secs} seconds, "
            "or contact registry@acity.edu.gh for urgent queries.\n\n"
            "💬 Anything else I can help with? I'm Kai — always here for questions on fees, registration, courses, exams, hostels, and more!"
        )

    last_error = None
    for idx, key in available:
        try:
            print(f"[API Rotation] Trying key {idx+1}/{len(keys)}...")
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents=prompt
                # No thinking_config — fastest possible response
            )
            print(f"[API Rotation] Key {idx+1} succeeded ✅")
            result = response.text
            _set_cached(question, result)
            return result

        except Exception as e:
            err = str(e)
            last_error = e
            print(f"[API Rotation] Key {idx+1} failed: {err[:200]}")

            if "FAILED_PRECONDITION" in err or "PERMISSION_DENIED" in err or "location" in err.lower():
                # Likely a regional/permission issue — rest for 1 hour, not permanent
                _cooldown(idx, 3600)
            elif "429" in err or "RESOURCE_EXHAUSTED" in err:
                # Rate limit — rest for 65 seconds then recover
                _cooldown(idx, 65)
            # Any other error: skip this key for this request only (no cooldown)
            continue

    print(f"[API Rotation] All available key(s) exhausted. Last error: {last_error}")
    return (
        "I'm experiencing high demand right now. Please try again in a few minutes "
        "or contact registry@acity.edu.gh for urgent queries.\n\n"
        "💬 Anything else I can help with? I'm Kai — always here for questions on fees, registration, courses, exams, hostels, and more!"
    )
