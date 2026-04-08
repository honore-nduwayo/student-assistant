import os
import time
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


# ─────────────────────────────────────────────────────────────
# ACADEMIC CALENDAR — DYNAMIC (Firestore) WITH HARDCODED FALLBACK
#
# HOW ADMINS UPDATE IT (no code change needed):
#   In Firebase Console → Firestore → settings → academic_calendar
#   set fields: semester_1_start, semester_1_end, semester_2_start,
#   semester_2_end, exam_1_start, exam_1_end, exam_2_start, exam_2_end,
#   break_start, break_end, academic_year, semester_2_label_end, exam_2_label
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
                "exam_1_start", "exam_1_end",
                "exam_2_start", "exam_2_end",
                "break_start", "break_end",
            ]
            if all(k in data for k in required):
                _calendar_cache = data
                _calendar_cache_ts = now
                print("[Calendar] Loaded from Firestore ✅")
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

    if in_range("exam_1_start",     "exam_1_end"):     return "Semester 1 Examination Period"
    if in_range("exam_2_start",     "exam_2_end"):     return "Semester 2 Examination Period"
    if in_range("semester_1_start", "semester_1_end"): return "Semester 1 (classes in session)"
    if in_range("semester_2_start", "semester_2_end"): return "Semester 2 (classes in session)"
    if in_range("break_start",      "break_end"):      return "Semester Break / Vacation"
    return "Pre-semester / Registration Period"


# ─────────────────────────────────────────────────────────────
# KEYWORD → URL MAP
# ─────────────────────────────────────────────────────────────

KEYWORD_URL_MAP = [
    {"label": "about_general", "keywords": ["about", "what is acity", "academic city", "overview", "who is", "tell me about", "acity university", "advantage", "why acity", "unique", "special"], "urls": ["https://acity.edu.gh/", "https://acity.edu.gh/about/", "https://acity.edu.gh/the-acity-advantage/"]},
    {"label": "history", "keywords": ["history", "founded", "established", "origin", "when was", "how old", "started", "creation", "our history"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#our-history"]},
    {"label": "vision_mission", "keywords": ["vision", "mission", "values", "goals", "purpose", "philosophy", "objective", "mandate", "commitment"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#vision_and_mission"]},
    {"label": "accreditation", "keywords": ["accredited", "accreditation", "nab", "recognized", "approved", "legitimate", "legit", "certified", "national accreditation", "valid degree", "is acity accredited"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#accreditation"]},
    {"label": "global_partners", "keywords": ["partners", "partnerships", "international", "global", "collaboration", "mou", "exchange", "affiliate", "foreign university", "sister school"], "urls": ["https://acity.edu.gh/about/", "https://acity.edu.gh/about/#global_partners"]},
    {"label": "leadership", "keywords": ["leadership", "vice chancellor", "vc", "president", "rector", "management", "executive", "governing council", "who leads", "administration", "head", "chancellor", "mcbagonluri", "provost", "dean", "director", "executive team"], "urls": ["https://acity.edu.gh/about/#university-leadership", "https://acity.edu.gh/about/executive-team/", "https://acity.edu.gh/about/governing-council/"]},
    {"label": "contact", "keywords": ["contact", "phone", "email", "reach", "call", "whatsapp", "helpdesk", "support", "inquire", "enquire", "get in touch", "office hours", "telephone"], "urls": ["https://acity.edu.gh/contact-connect/", "https://acity.edu.gh/registry/"]},
    {"label": "location_visit", "keywords": ["location", "where is", "address", "campus", "directions", "map", "how to get", "visit", "find acity", "landmark", "near", "east legon", "accra", "haatso"], "urls": ["https://acity.edu.gh/visit/", "https://acity.edu.gh/contact-connect/"]},
    {"label": "student_app", "keywords": ["student app", "acity app", "acityplus", "acity+", "mobile app", "app download", "portal app", "student portal", "online portal", "acityplus login", "acity plus", "login portal"], "urls": ["https://acity.edu.gh/student-app/", "https://acityplus.acity.edu.gh/"]},
    {"label": "library", "keywords": ["library", "books", "journals", "research material", "database", "e-library", "reading room", "borrow", "lending"], "urls": ["https://acity.edu.gh/library/", "https://acity.edu.gh/academic-resources/"]},
    {"label": "careers_jobs", "keywords": ["job", "jobs", "career", "vacancy", "vacancies", "employment", "work at acity", "hiring", "recruitment", "staff position", "lecturer position", "apply for job"], "urls": ["https://acity.edu.gh/careers-at-acity/"]},
    {"label": "staff_directory", "keywords": ["staff directory", "staff list", "find staff", "faculty list", "lecturer name", "professor name", "who teaches", "find lecturer", "find professor"], "urls": ["https://acity.edu.gh/academic-city-staff-directory/"]},
    {"label": "undergraduate_all", "keywords": ["undergraduate", "bachelor", "bsc", "bba", "ba", "degree programme", "4 year", "four year", "what programmes", "what courses", "all programmes", "list of programmes", "available courses", "offered"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering"]},
    {"label": "engineering", "keywords": ["engineering", "computer engineering", "electrical engineering", "electronics", "mechanical engineering", "biomedical engineering", "robotics engineering", "bsc engineering", "faculty of engineering", "mechanical", "biomedical", "robotics"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering"]},
    {"label": "informatics", "keywords": ["computer science", "cs", "information technology", "it", "artificial intelligence", "ai", "informatics", "bsc cs", "bsc it", "bsc ai", "software", "machine learning", "programming degree", "data science"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#informatics"]},
    {"label": "business", "keywords": ["business", "bba", "accounting", "marketing", "finance", "banking", "entrepreneurship", "management", "commerce", "faculty of business"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#business"]},
    {"label": "communication_arts", "keywords": ["communication", "journalism", "mass communication", "mass comm", "advertising", "public relations", "pr", "media studies", "ba communication", "communication arts"], "urls": ["https://acity.edu.gh/undergraduate-programmes/", "https://acity.edu.gh/undergraduate-programmes/#communication-arts"]},
    {"label": "graduate", "keywords": ["graduate", "postgraduate", "masters", "msc", "mba", "phd", "graduate school", "msc cybersecurity", "msc data science", "data analytics", "graduate programme"], "urls": ["https://acity.edu.gh/graduate-programmes/"]},
    {"label": "professional_certificate", "keywords": ["certificate", "professional certificate", "short course", "diploma", "cpd", "continuing education", "professional development", "part time", "evening programme"], "urls": ["https://acity.edu.gh/professional-certificate-programmes/"]},
    {"label": "enrollment_courses", "keywords": ["enroll", "enrollment", "add course", "drop course", "change course", "change major", "timetable", "class schedule", "course registration", "hod", "head of department", "credit hours", "units", "elective", "core course"], "urls": ["https://acity.edu.gh/academic-resources/", "https://acity.edu.gh/registry/"]},
    {"label": "admissions_apply", "keywords": ["apply", "application", "how to apply", "admission", "apply online", "admissions portal", "application form", "entry requirements", "wassce", "sssce", "a levels", "ib diploma", "sat", "qualification", "eligibility", "freshman", "new student", "prospective student", "intake", "cohort", "september intake", "january intake", "start application"], "urls": ["https://acity.edu.gh/start-your-application/", "https://acity.edu.gh/entry-requirements/", "https://admissions.acity.edu.gh/undergraduate"]},
    {"label": "registry", "keywords": ["registry", "registrar", "student id", "matric number", "transcript", "clearance", "graduation clearance", "deferral", "verification letter", "official letter", "academic records", "registration office"], "urls": ["https://acity.edu.gh/registry/"]},
    {"label": "fees_tuition", "keywords": ["fee", "fees", "tuition", "cost", "how much", "price", "ghs", "usd", "cedis", "pay", "payment", "amount", "charges", "billing", "invoice", "receipt"], "urls": ["https://acity.edu.gh/fees-scholarships/", "https://acity.edu.gh/finance-billing/"]},
    {"label": "scholarships", "keywords": ["scholarship", "bursary", "financial aid", "grant", "discount", "free tuition", "sponsored", "merit award", "need based", "fellowship", "sponsorship"], "urls": ["https://acity.edu.gh/fees-scholarships/"]},
    {"label": "finance_payment", "keywords": ["pay fees", "how to pay", "payment method", "bank transfer", "mobile money", "momo", "mtn momo", "vodafone cash", "finance office", "installment", "payment deadline"], "urls": ["https://acity.edu.gh/finance-billing/"]},
    {"label": "exams_results", "keywords": ["exam", "exams", "examination", "test", "quiz", "assessment", "result", "results", "grade", "grades", "gpa", "cgpa", "score", "transcript", "resit", "repeat exam", "supplementary", "academic standing", "pass", "fail", "grade report", "check result"], "urls": ["https://acity.edu.gh/academic-resources/", "https://acityplus.acity.edu.gh/login", "https://acity.edu.gh/registry/"]},
    {"label": "academic_calendar", "keywords": ["academic calendar", "semester", "semester dates", "when does semester", "school calendar", "term dates", "vacation", "break", "holiday", "reading week", "exam period", "exam timetable", "exam schedule"], "urls": ["https://acity.edu.gh/academic-resources/"]},
    {"label": "graduation", "keywords": ["graduation", "convocation", "ceremony", "certificate collection", "graduation gown", "when is graduation", "graduation requirements", "complete my degree", "finished degree", "graduate soon"], "urls": ["https://acity.edu.gh/registry/", "https://acity.edu.gh/academic-resources/"]},
    {"label": "hostel_accommodation", "keywords": ["hostel", "accommodation", "housing", "room", "dormitory", "dorm", "on campus", "residential", "stay on campus", "bed space", "live on campus", "aclife", "student housing"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#aclife"]},
    {"label": "dining", "keywords": ["dining", "food", "canteen", "cafeteria", "meal plan", "lunch", "breakfast", "dinner", "eat on campus", "restaurant", "meal ticket"], "urls": ["https://acity.edu.gh/student-life/dining-meal-plans/"]},
    {"label": "health_wellness", "keywords": ["health", "wellness", "clinic", "doctor", "sick", "nurse", "mental health", "counseling", "counselling", "hospital", "medical", "health center", "health centre"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#health_&_wellness"]},
    {"label": "sports_recreation", "keywords": ["sports", "recreation", "gym", "football", "basketball", "tennis", "exercise", "fitness", "athletics", "games", "swimming", "sport facilities", "volleyball"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#sports_and_recreation"]},
    {"label": "clubs_societies", "keywords": ["club", "clubs", "societies", "student activities", "extracurricular", "associations", "groups", "student organization", "join a club", "society"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#clubs_at_acity"]},
    {"label": "student_council", "keywords": ["student council", "src", "acsc", "student government", "student union", "student representative", "student body", "student affairs", "student commitment"], "urls": ["https://acity.edu.gh/student-life/", "https://acity.edu.gh/student-life/#academic_city_student_council"]},
    {"label": "career_services", "keywords": ["career services", "internship", "job placement", "cv writing", "resume", "interview prep", "industry placement", "work experience", "career fair", "career center", "career centre"], "urls": ["https://acity.edu.gh/student-life/career-services/"]},
]


# ── Domains that block scraping ───────────────────────────────
SKIP_LIVE_FETCH = {
    "twitter.com", "x.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com",
}

MAX_LIVE_URLS = 1  # reduced from 2 to cut token usage


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
    print(f"[URL Router] fallback → {result}")
    return result or ["https://acity.edu.gh/"]


# ── Topic detection ───────────────────────────────────────────
TOPIC_KEYWORDS = {
    "fees": ["fee", "fees", "cost", "pay", "payment", "tuition", "amount", "price", "ghs", "cedis", "scholarship", "financial", "bursary", "receipt", "billing"],
    "registration": ["register", "registration", "admit", "admission", "apply", "application", "form", "portal", "login", "password", "student id", "matric", "entry requirement", "wassce"],
    "exams": ["exam", "exams", "test", "quiz", "assessment", "result", "grade", "score", "gpa", "cgpa", "transcript", "resit", "repeat", "academic calendar", "semester", "timetable"],
    "hostel": ["hostel", "accommodation", "room", "bed", "dorm", "dormitory", "residential", "housing", "live", "stay", "campus life", "dining", "meal"],
    "enrollment": ["enroll", "enrollment", "course", "courses", "credit", "unit", "timetable", "schedule", "hod", "department", "programme", "major", "elective", "add", "drop", "computer science", "bsc", "bba", "ba", "engineering"],
}

def detect_topic(question: str) -> str:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


# ── Page scraper — 30-min cache, 1500 char limit ──────────────
_page_cache: dict = {}
CACHE_TTL = 1800  # 30 minutes

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
        content = " ".join(text.split())[:1500]  # reduced from 3000
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


# ── Real-time context ─────────────────────────────────────────
def get_dynamic_context() -> str:
    now      = datetime.now(ZoneInfo("Africa/Accra"))
    day_name = now.strftime("%A")
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%B %d, %Y")
    hour     = now.hour
    weekday  = now.weekday()
    is_office_hrs = (weekday < 5) and (8 <= hour < 17)
    office_status = "OPEN (Mon–Fri, 8 AM–5 PM GMT)" if is_office_hrs else "CLOSED right now"
    cal = get_academic_calendar()
    current_period = _detect_current_period(now, cal)
    academic_year     = cal.get("academic_year",        FALLBACK_CALENDAR["academic_year"])
    sem2_label_end    = cal.get("semester_2_label_end", FALLBACK_CALENDAR["semester_2_label_end"])
    exam2_label       = cal.get("exam_2_label",         FALLBACK_CALENDAR["exam_2_label"])
    return (
        f"[CONTEXT] Date: {date_str} ({day_name}) | Time: {time_str} GMT | "
        f"Period: {current_period} | Sem 2 ends: {sem2_label_end} | "
        f"Exam 2: {exam2_label} | Offices: {office_status} | Year: {academic_year}"
    )


# ── Main AI Response Function ─────────────────────────────────
def get_ai_response(question: str, knowledge_base: list, history: list) -> str:

    topic = detect_topic(question)

    # Live page content (1 URL, 1500 chars max)
    live_content = fetch_live_content(question)

    # Real-time context (single line)
    dynamic_context = get_dynamic_context()

    # KB: filter by topic first, fall back to general, cap at 25 entries
    relevant = [e for e in knowledge_base if e.get("active", True) and e.get("topic") == topic]
    if len(relevant) < 10:
        relevant += [e for e in knowledge_base if e.get("active", True) and e.get("topic") != topic]
    relevant = relevant[:25]
    kb_text = "".join(
        f"Q: {e.get('question','')}\nA: {e.get('answer','')}\n"
        for e in relevant
    )

    # History: last 5 exchanges only
    history_text = ""
    for msg in history[-5:]:
        role = "Student" if msg.get("role") == "user" else "Kai"
        history_text += f"{role}: {msg.get('text', '')}\n"

    prompt = f"""You are Kai, the official AI student assistant for Academic City University College (ACity), Accra, Ghana.
Be warm, concise, and accurate. Only answer ACity-related questions.

FORMATTING:
- Use numbered steps (Step 1:, Step 2:) for any process or procedure.
- Use bullet points (•) for lists of facts.
- Bold (**term**) key terms only.
- Write plain URLs after a colon — never markdown links: RIGHT: visit: https://acity.edu.gh  WRONG: [visit](https://acity.edu.gh)
- Keep answers focused — no long paragraphs.

ANSWER PRIORITY:
1. KNOWLEDGE BASE below — use it first.
2. LIVE CONTENT below — use if KB has nothing.
3. REAL-TIME CONTEXT — use for dates, semester, office hours.
4. If still unknown, say so and direct to registry@acity.edu.gh.

END every response with exactly:
"💬 Anything else I can help with? Always here for questions on fees, registration, courses, exams, hostels, and more!"

{dynamic_context}

HISTORY:
{history_text}

KNOWLEDGE BASE (topic: {topic}):
{kb_text}

LIVE CONTENT:
{live_content}

Student: {question}
Kai:"""

    keys = get_api_keys()
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

    print(f"[API Rotation] {len(keys)} key(s) — model: {model}")

    if not keys:
        return "I'm having a configuration issue. Please contact registry@acity.edu.gh for help."

    last_error = None
    for i, key in enumerate(keys, 1):
        try:
            print(f"[API Rotation] Trying key {i}/{len(keys)}...")
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="none")
                )
            )
            print(f"[API Rotation] Key {i} succeeded ✅")
            return response.text
        except Exception as e:
            last_error = e
            print(f"[API Rotation] Key {i} failed: {str(e)[:200]}")
            continue

    print(f"[API Rotation] All {len(keys)} key(s) exhausted. Last error: {last_error}")
    return (
        "I'm experiencing high demand right now. Please try again in a few minutes "
        "or contact registry@acity.edu.gh for urgent queries."
    )
