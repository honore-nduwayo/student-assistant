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
# HOW IT WORKS:
#   1. On first call, try to load the calendar from the Firestore
#      document: settings/academic_calendar
#   2. Cache the result for CALENDAR_CACHE_TTL seconds (6 hours)
#      so we don't hit Firestore on every request.
#   3. If Firestore is unavailable or the document doesn't exist,
#      fall back to FALLBACK_CALENDAR automatically.
#
# HOW ADMINS UPDATE IT (no code change needed):
#   In Firebase Console → Firestore → settings → academic_calendar
#   set these fields:
#
#     semester_1_start  : "2026-09-01"
#     semester_1_end    : "2026-12-20"
#     semester_2_start  : "2027-01-12"
#     semester_2_end    : "2027-05-10"
#     exam_1_start      : "2026-12-08"
#     exam_1_end        : "2026-12-20"
#     exam_2_start      : "2027-04-27"
#     exam_2_end        : "2027-05-10"
#     break_start       : "2026-12-21"
#     break_end         : "2027-01-11"
#     academic_year     : "2026–2027"
#     semester_2_label_end : "May 10, 2027"
#     exam_2_label      : "April 27 – May 10, 2027"
#
#   The bot picks up the new dates within 6 hours automatically,
#   or immediately if you restart the server.
#
# FALLBACK_CALENDAR is only used when Firestore is unreachable.
# Update it once per year as a safety net.
# ─────────────────────────────────────────────────────────────

FALLBACK_CALENDAR = {
    "semester_1_start":   "2025-09-01",
    "semester_1_end":     "2025-12-20",
    "semester_2_start":   "2026-01-12",
    "semester_2_end":     "2026-05-10",
    "exam_1_start":       "2025-12-08",
    "exam_1_end":         "2025-12-20",
    "exam_2_start":       "2026-04-27",
    "exam_2_end":         "2026-05-10",
    "break_start":        "2025-12-21",
    "break_end":          "2026-01-11",
    "academic_year":      "2025–2026",
    "semester_2_label_end": "May 10, 2026",
    "exam_2_label":       "April 27 – May 10, 2026",
}

CALENDAR_CACHE_TTL = 21600  # 6 hours — same as KB cache
_calendar_cache: dict | None = None
_calendar_cache_ts: float = 0.0


def get_academic_calendar() -> dict:
    """
    Returns the academic calendar dict.
    Tries Firestore first (cached for 6 hours), falls back to
    FALLBACK_CALENDAR if unavailable.
    """
    global _calendar_cache, _calendar_cache_ts

    now = time.time()
    if _calendar_cache and (now - _calendar_cache_ts) < CALENDAR_CACHE_TTL:
        return _calendar_cache

    try:
        # Import here to avoid circular import issues
        from services.database import db
        doc = db.collection("settings").document("academic_calendar").get()
        if doc.exists:
            data = doc.to_dict()
            # Validate that the required keys are present
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
                print("[Calendar] Loaded from Firestore ✅")
                return _calendar_cache
            else:
                print("[Calendar] Firestore doc incomplete — using fallback")
        else:
            print("[Calendar] Firestore doc not found — using fallback")
    except Exception as e:
        print(f"[Calendar] Firestore error ({e}) — using fallback")

    # Use hardcoded fallback
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
#
# Each entry has:
#   "keywords" : words/phrases — if ANY appear in the student's
#                question, this entry scores a hit.
#   "urls"     : ordered list of pages to scrape for that topic
#                (most specific / most useful page listed first).
#   "label"    : short tag used only in debug logs.
#
# HOW IT WORKS:
#   detect_live_urls(question) scores every entry by counting
#   keyword hits, then returns the top-scoring URLs (up to
#   MAX_LIVE_URLS). Those pages are scraped and injected into
#   the Gemini prompt as live context so Gemini always has
#   fresh, accurate ACity data — even if the Firestore KB is
#   missing that information.
#
# SOCIAL MEDIA NOTE:
#   Twitter/X, Facebook, Instagram, LinkedIn, and YouTube all
#   block server-side scrapers (they return login walls or empty
#   HTML). The ACity-specific paths are listed here so Gemini
#   knows they exist and can mention them to students, but they
#   are excluded from live fetching via SKIP_LIVE_FETCH.
#   The generic roots (twitter.com/, facebook.com/ etc.) contain
#   no ACity information so they are intentionally omitted.
# ─────────────────────────────────────────────────────────────

KEYWORD_URL_MAP = [

    # ── ABOUT / GENERAL ──────────────────────────────────────
    {
        "label": "about_general",
        "keywords": [
            "about", "what is acity", "academic city", "overview",
            "who is", "tell me about", "acity university",
            "advantage", "why acity", "unique", "special"
        ],
        "urls": [
            "https://acity.edu.gh/",
            "https://acity.edu.gh/about/",
            "https://acity.edu.gh/the-acity-advantage/",
        ]
    },

    # ── HISTORY ──────────────────────────────────────────────
    {
        "label": "history",
        "keywords": [
            "history", "founded", "established", "origin",
            "when was", "how old", "started", "creation", "our history"
        ],
        "urls": [
            "https://acity.edu.gh/about/",
            "https://acity.edu.gh/about/#our-history",
        ]
    },

    # ── VISION & MISSION ─────────────────────────────────────
    {
        "label": "vision_mission",
        "keywords": [
            "vision", "mission", "values", "goals", "purpose",
            "philosophy", "objective", "mandate", "commitment"
        ],
        "urls": [
            "https://acity.edu.gh/about/",
            "https://acity.edu.gh/about/#vision_and_mission",
        ]
    },

    # ── ACCREDITATION ────────────────────────────────────────
    {
        "label": "accreditation",
        "keywords": [
            "accredited", "accreditation", "nab", "recognized",
            "approved", "legitimate", "legit", "certified",
            "national accreditation", "valid degree", "is acity accredited"
        ],
        "urls": [
            "https://acity.edu.gh/about/",
            "https://acity.edu.gh/about/#accreditation",
        ]
    },

    # ── GLOBAL PARTNERS ──────────────────────────────────────
    {
        "label": "global_partners",
        "keywords": [
            "partners", "partnerships", "international", "global",
            "collaboration", "mou", "exchange", "affiliate",
            "foreign university", "sister school"
        ],
        "urls": [
            "https://acity.edu.gh/about/",
            "https://acity.edu.gh/about/#global_partners",
        ]
    },

    # ── LEADERSHIP / GOVERNANCE ──────────────────────────────
    {
        "label": "leadership",
        "keywords": [
            "leadership", "vice chancellor", "vc", "president",
            "rector", "management", "executive", "governing council",
            "who leads", "administration", "head", "chancellor",
            "mcbagonluri", "provost", "dean", "director", "executive team"
        ],
        "urls": [
            "https://acity.edu.gh/about/#university-leadership",
            "https://acity.edu.gh/about/executive-team/",
            "https://acity.edu.gh/about/governing-council/",
            "https://acity.edu.gh/prof-mcbagonluri-named-among-africas-top-education-leaders/",
        ]
    },

    # ── CONTACT ──────────────────────────────────────────────
    {
        "label": "contact",
        "keywords": [
            "contact", "phone", "email", "reach", "call",
            "whatsapp", "helpdesk", "support", "inquire",
            "enquire", "get in touch", "office hours", "telephone"
        ],
        "urls": [
            "https://acity.edu.gh/contact-connect/",
            "https://acity.edu.gh/registry/",
        ]
    },

    # ── LOCATION / VISIT / CAMPUS ────────────────────────────
    {
        "label": "location_visit",
        "keywords": [
            "location", "where is", "address", "campus", "directions",
            "map", "how to get", "visit", "find acity", "landmark",
            "near", "east legon", "accra", "haatso"
        ],
        "urls": [
            "https://acity.edu.gh/visit/",
            "https://acity.edu.gh/virtual-tour/",
            "https://acity.edu.gh/contact-connect/",
        ]
    },

    # ── VIRTUAL TOUR ─────────────────────────────────────────
    {
        "label": "virtual_tour",
        "keywords": [
            "virtual tour", "campus tour", "explore campus",
            "online tour", "3d tour", "see campus", "view campus"
        ],
        "urls": [
            "https://acity.edu.gh/virtual-tour/",
        ]
    },

    # ── STUDENT APP / ACITYPLUS ──────────────────────────────
    {
        "label": "student_app",
        "keywords": [
            "student app", "acity app", "acityplus", "acity+",
            "mobile app", "app download", "portal app", "student portal",
            "online portal", "acityplus login", "acity plus", "login portal"
        ],
        "urls": [
            "https://acity.edu.gh/student-app/",
            "https://acityplus.acity.edu.gh/",
            "https://acityplus.acity.edu.gh/login",
        ]
    },

    # ── LIBRARY ──────────────────────────────────────────────
    {
        "label": "library",
        "keywords": [
            "library", "books", "journals", "research material",
            "database", "e-library", "reading room", "borrow", "lending"
        ],
        "urls": [
            "https://acity.edu.gh/library/",
            "https://acity.edu.gh/academic-resources/",
        ]
    },

    # ── CAREERS AT ACITY (JOBS) ──────────────────────────────
    {
        "label": "careers_jobs",
        "keywords": [
            "job", "jobs", "career", "vacancy", "vacancies",
            "employment", "work at acity", "hiring", "recruitment",
            "staff position", "lecturer position", "apply for job"
        ],
        "urls": [
            "https://acity.edu.gh/careers-at-acity/",
        ]
    },

    # ── MEDIA / NEWSLETTER / BLOG ────────────────────────────
    {
        "label": "media_news",
        "keywords": [
            "newsletter", "blog", "news", "updates", "exponent",
            "magazine", "press", "media", "announcement",
            "latest news", "articles", "publications"
        ],
        "urls": [
            "https://acity.edu.gh/blog/",
            "https://acity.edu.gh/the-exponent-acity-newsletter/",
            "https://acity.edu.gh/media-relations/",
            "https://acity.edu.gh/author/blogeditor/",
        ]
    },

    # ── PRIVACY POLICY ───────────────────────────────────────
    {
        "label": "privacy",
        "keywords": [
            "privacy", "data protection", "personal data",
            "policy", "cookies", "gdpr", "information security"
        ],
        "urls": [
            "https://acity.edu.gh/privacy-policy/",
        ]
    },

    # ── STAFF DIRECTORY ──────────────────────────────────────
    {
        "label": "staff_directory",
        "keywords": [
            "staff directory", "staff list", "find staff",
            "faculty list", "lecturer name", "professor name",
            "who teaches", "find lecturer", "find professor"
        ],
        "urls": [
            "https://acity.edu.gh/academic-city-staff-directory/",
        ]
    },

    # ── STUDENT CORNER / STAFF CORNER ────────────────────────
    {
        "label": "student_staff_corner",
        "keywords": [
            "student corner", "staff corner", "student resources",
            "staff resources", "student area", "staff area",
            "student hub", "resources for students"
        ],
        "urls": [
            "https://acity.edu.gh/student-corner/",
            "https://acity.edu.gh/staff-corner/",
        ]
    },

    # ── COMMUNITY ENGAGEMENT / CSR ───────────────────────────
    {
        "label": "community_engagement",
        "keywords": [
            "community", "csr", "social responsibility", "donation",
            "outreach", "impact", "engagement", "schools",
            "galamsey", "digital learning", "tech expo"
        ],
        "urls": [
            "https://acity.edu.gh/category/acity-community-engagement/",
            "https://acity.edu.gh/academic-city-supports-digital-learning-with-donation-to-ga-east-schools/",
            "https://acity.edu.gh/academic-citys-tech-expo-showcases-innovative-technologies-to-tackle-galamsey/",
        ]
    },

    # ── ACITY FOUNDATION ─────────────────────────────────────
    {
        "label": "acity_foundation",
        "keywords": [
            "foundation", "acity foundation", "philanthropy",
            "charity", "social impact", "nonprofit", "acityfoundation"
        ],
        "urls": [
            "https://acityfoundation.org/",
        ]
    },

    # ── INNOVATION / RESEARCH ────────────────────────────────
    {
        "label": "innovation_research",
        "keywords": [
            "innovation", "innovates", "research", "tech expo",
            "project", "startup", "hackathon", "invention",
            "technology initiative", "stem", "acity innovates"
        ],
        "urls": [
            "https://acity.edu.gh/category/acity-innovates/",
            "https://acity.edu.gh/academic-citys-tech-expo-showcases-innovative-technologies-to-tackle-galamsey/",
            "https://acity.edu.gh/blog/",
        ]
    },

    # ── COLLABORATION NEWS ───────────────────────────────────
    {
        "label": "collaboration_news",
        "keywords": [
            "collaborates", "collaboration", "partner news",
            "ambassador", "japan", "korea", "mozambique",
            "diplomacy", "international relations", "global ties",
            "mou signed", "agreement"
        ],
        "urls": [
            "https://acity.edu.gh/category/acity-collaborates/",
            "https://acity.edu.gh/strengthening-global-ties-academic-city-engages-ambassadors-of-japan-korea-and-mozambique/",
        ]
    },

    # ── ACITY SHINE (ACHIEVEMENTS) ───────────────────────────
    {
        "label": "acity_shine",
        "keywords": [
            "shine", "achievement", "award", "recognition",
            "student achievement", "proud", "honour", "honor",
            "ranked", "best", "top student", "mcbagonluri award"
        ],
        "urls": [
            "https://acity.edu.gh/category/acity-shine/",
            "https://acity.edu.gh/prof-mcbagonluri-named-among-africas-top-education-leaders/",
        ]
    },

    # ── UNDERGRADUATE PROGRAMMES (OVERVIEW) ──────────────────
    {
        "label": "undergraduate_all",
        "keywords": [
            "undergraduate", "bachelor", "bsc", "bba", "ba",
            "degree programme", "4 year", "four year",
            "what programmes", "what courses", "all programmes",
            "list of programmes", "available courses", "offered"
        ],
        "urls": [
            "https://acity.edu.gh/undergraduate-programmes/",
            "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering",
            "https://acity.edu.gh/undergraduate-programmes/#informatics",
            "https://acity.edu.gh/undergraduate-programmes/#business",
            "https://acity.edu.gh/undergraduate-programmes/#communication-arts",
        ]
    },

    # ── ENGINEERING ──────────────────────────────────────────
    {
        "label": "engineering",
        "keywords": [
            "engineering", "computer engineering", "electrical engineering",
            "electronics", "mechanical engineering", "biomedical engineering",
            "robotics engineering", "bsc engineering", "faculty of engineering",
            "mechanical", "biomedical", "robotics"
        ],
        "urls": [
            "https://acity.edu.gh/undergraduate-programmes/",
            "https://acity.edu.gh/undergraduate-programmes/#faculty-of-engineering",
        ]
    },

    # ── INFORMATICS / CS / AI / IT ───────────────────────────
    {
        "label": "informatics",
        "keywords": [
            "computer science", "cs", "information technology", "it",
            "artificial intelligence", "ai", "informatics",
            "bsc cs", "bsc it", "bsc ai", "software",
            "machine learning", "programming degree", "data science"
        ],
        "urls": [
            "https://acity.edu.gh/undergraduate-programmes/",
            "https://acity.edu.gh/undergraduate-programmes/#informatics",
        ]
    },

    # ── BUSINESS ─────────────────────────────────────────────
    {
        "label": "business",
        "keywords": [
            "business", "bba", "accounting", "marketing",
            "finance", "banking", "entrepreneurship",
            "management", "commerce", "faculty of business"
        ],
        "urls": [
            "https://acity.edu.gh/undergraduate-programmes/",
            "https://acity.edu.gh/undergraduate-programmes/#business",
        ]
    },

    # ── COMMUNICATION ARTS ───────────────────────────────────
    {
        "label": "communication_arts",
        "keywords": [
            "communication", "journalism", "mass communication",
            "mass comm", "advertising", "public relations", "pr",
            "media studies", "ba communication", "communication arts"
        ],
        "urls": [
            "https://acity.edu.gh/undergraduate-programmes/",
            "https://acity.edu.gh/undergraduate-programmes/#communication-arts",
        ]
    },

    # ── GRADUATE / POSTGRADUATE ──────────────────────────────
    {
        "label": "graduate",
        "keywords": [
            "graduate", "postgraduate", "masters", "msc", "mba",
            "phd", "graduate school", "msc cybersecurity",
            "msc data science", "data analytics", "graduate programme"
        ],
        "urls": [
            "https://acity.edu.gh/graduate-programmes/",
            "https://acity.edu.gh/graduate-programmes/#graduate-programmes",
        ]
    },

    # ── PROFESSIONAL CERTIFICATES ────────────────────────────
    {
        "label": "professional_certificate",
        "keywords": [
            "certificate", "professional certificate", "short course",
            "diploma", "cpd", "continuing education",
            "professional development", "part time", "evening programme"
        ],
        "urls": [
            "https://acity.edu.gh/professional-certificate-programmes/",
        ]
    },

    # ── COURSE ENROLLMENT / TIMETABLE ────────────────────────
    {
        "label": "enrollment_courses",
        "keywords": [
            "enroll", "enrollment", "add course", "drop course",
            "change course", "change major", "timetable", "class schedule",
            "course registration", "hod", "head of department",
            "credit hours", "units", "elective", "core course"
        ],
        "urls": [
            "https://acity.edu.gh/academic-resources/",
            "https://acity.edu.gh/registry/",
            "https://acityplus.acity.edu.gh/",
            "https://acityplus.acity.edu.gh/login",
        ]
    },

    # ── ADMISSIONS / APPLICATION ─────────────────────────────
    {
        "label": "admissions_apply",
        "keywords": [
            "apply", "application", "how to apply", "admission",
            "apply online", "admissions portal", "application form",
            "entry requirements", "wassce", "sssce", "a levels",
            "ib diploma", "sat", "qualification", "eligibility",
            "freshman", "new student", "prospective student",
            "intake", "cohort", "september intake", "january intake",
            "start application"
        ],
        "urls": [
            "https://acity.edu.gh/start-your-application/",
            "https://acity.edu.gh/entry-requirements/",
            "https://admissions.acity.edu.gh/",
            "https://admissions.acity.edu.gh/undergraduate",
        ]
    },

    # ── REGISTRY ─────────────────────────────────────────────
    {
        "label": "registry",
        "keywords": [
            "registry", "registrar", "student id", "matric number",
            "transcript", "clearance", "graduation clearance",
            "deferral", "verification letter", "official letter",
            "academic records", "registration office"
        ],
        "urls": [
            "https://acity.edu.gh/registry/",
        ]
    },

    # ── FEES / TUITION ───────────────────────────────────────
    {
        "label": "fees_tuition",
        "keywords": [
            "fee", "fees", "tuition", "cost", "how much",
            "price", "ghs", "usd", "cedis", "pay", "payment",
            "amount", "charges", "billing", "invoice", "receipt"
        ],
        "urls": [
            "https://acity.edu.gh/fees-scholarships/",
            "https://acity.edu.gh/finance-billing/",
        ]
    },

    # ── SCHOLARSHIPS / FINANCIAL AID ─────────────────────────
    {
        "label": "scholarships",
        "keywords": [
            "scholarship", "bursary", "financial aid", "grant",
            "discount", "free tuition", "sponsored", "merit award",
            "need based", "fellowship", "sponsorship"
        ],
        "urls": [
            "https://acity.edu.gh/fees-scholarships/",
        ]
    },

    # ── FINANCE / PAYMENT METHODS ────────────────────────────
    {
        "label": "finance_payment",
        "keywords": [
            "pay fees", "how to pay", "payment method", "bank transfer",
            "mobile money", "momo", "mtn momo", "vodafone cash",
            "finance office", "installment", "payment deadline"
        ],
        "urls": [
            "https://acity.edu.gh/finance-billing/",
        ]
    },

    # ── EXAMS / RESULTS / GRADES ─────────────────────────────
    {
        "label": "exams_results",
        "keywords": [
            "exam", "exams", "examination", "test", "quiz",
            "assessment", "result", "results", "grade", "grades",
            "gpa", "cgpa", "score", "transcript", "resit",
            "repeat exam", "supplementary", "academic standing",
            "pass", "fail", "grade report", "check result"
        ],
        "urls": [
            "https://acity.edu.gh/academic-resources/",
            "https://acityplus.acity.edu.gh/login",
            "https://acity.edu.gh/registry/",
        ]
    },

    # ── ACADEMIC CALENDAR / SEMESTER ─────────────────────────
    {
        "label": "academic_calendar",
        "keywords": [
            "academic calendar", "semester", "semester dates",
            "when does semester", "school calendar", "term dates",
            "vacation", "break", "holiday", "reading week",
            "exam period", "exam timetable", "exam schedule"
        ],
        "urls": [
            "https://acity.edu.gh/academic-resources/",
            "https://acityplus.acity.edu.gh/login",
        ]
    },

    # ── GRADUATION ───────────────────────────────────────────
    {
        "label": "graduation",
        "keywords": [
            "graduation", "convocation", "ceremony",
            "certificate collection", "graduation gown",
            "when is graduation", "graduation requirements",
            "complete my degree", "finished degree", "graduate soon"
        ],
        "urls": [
            "https://acity.edu.gh/registry/",
            "https://acity.edu.gh/academic-resources/",
        ]
    },

    # ── HOSTEL / ACCOMMODATION ───────────────────────────────
    {
        "label": "hostel_accommodation",
        "keywords": [
            "hostel", "accommodation", "housing", "room",
            "dormitory", "dorm", "on campus", "residential",
            "stay on campus", "bed space", "live on campus",
            "aclife", "student housing"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/",
            "https://acity.edu.gh/student-life/#aclife",
        ]
    },

    # ── DINING / MEAL PLANS ──────────────────────────────────
    {
        "label": "dining",
        "keywords": [
            "dining", "food", "canteen", "cafeteria", "meal plan",
            "lunch", "breakfast", "dinner", "eat on campus",
            "restaurant", "meal ticket"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/dining-meal-plans/",
        ]
    },

    # ── HEALTH & WELLNESS ────────────────────────────────────
    {
        "label": "health_wellness",
        "keywords": [
            "health", "wellness", "clinic", "doctor", "sick",
            "nurse", "mental health", "counseling", "counselling",
            "hospital", "medical", "health center", "health centre"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/",
            "https://acity.edu.gh/student-life/#health_&_wellness",
        ]
    },

    # ── SPORTS & RECREATION ──────────────────────────────────
    {
        "label": "sports_recreation",
        "keywords": [
            "sports", "recreation", "gym", "football", "basketball",
            "tennis", "exercise", "fitness", "athletics",
            "games", "swimming", "sport facilities", "volleyball"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/",
            "https://acity.edu.gh/student-life/#sports_and_recreation",
        ]
    },

    # ── CLUBS & SOCIETIES ────────────────────────────────────
    {
        "label": "clubs_societies",
        "keywords": [
            "club", "clubs", "societies", "student activities",
            "extracurricular", "associations", "groups",
            "student organization", "join a club", "society"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/",
            "https://acity.edu.gh/student-life/#clubs_at_acity",
        ]
    },

    # ── STUDENT COUNCIL / SRC ────────────────────────────────
    {
        "label": "student_council",
        "keywords": [
            "student council", "src", "acsc", "student government",
            "student union", "student representative", "student body",
            "student affairs", "student commitment"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/",
            "https://acity.edu.gh/student-life/#academic_city_student_council",
            "https://acity.edu.gh/student-life/#student_commitment",
        ]
    },

    # ── CAREER SERVICES ──────────────────────────────────────
    {
        "label": "career_services",
        "keywords": [
            "career services", "internship", "job placement",
            "cv writing", "resume", "interview prep",
            "industry placement", "work experience", "career fair",
            "career center", "career centre"
        ],
        "urls": [
            "https://acity.edu.gh/student-life/career-services/",
        ]
    },

    # ── SOCIAL MEDIA (reference only — NOT fetched live) ─────
    #
    # These URLs are here so Gemini knows about ACity's social
    # presence and can mention or link them to students in answers.
    # They are never actually scraped (see SKIP_LIVE_FETCH below)
    # because social platforms block server-side requests.
    #
    # Generic roots (twitter.com/, facebook.com/, etc.) are
    # intentionally excluded — they contain no ACity content.
    {
        "label": "social_media",
        "keywords": [
            "social media", "twitter", "facebook", "instagram",
            "linkedin", "youtube", "follow acity", "x.com", "@acitygh"
        ],
        "urls": [
            "https://twitter.com/acitygh/",
            "https://x.com/acitygh/",
            "https://www.facebook.com/acitygh/",
            "https://www.instagram.com/acitygh/",
            "https://www.linkedin.com/school/acitygh/",
            "https://www.youtube.com/channel/UCjPYPiE6JC0pHMbfrqVJ-qQ",
        ]
    },
]


# ── Domains that block scraping — skip live fetching for these ─
SKIP_LIVE_FETCH = {
    "twitter.com", "x.com", "facebook.com",
    "instagram.com", "linkedin.com", "youtube.com",
}

# Max live URLs to fetch per request (keeps response time fast)
MAX_LIVE_URLS = 2


# ── Score question against map and return best URLs ───────────
def detect_live_urls(question: str) -> list:
    """
    Scores every KEYWORD_URL_MAP entry by counting keyword hits
    in the student question. Returns the top-scoring, non-blocked
    URLs (up to MAX_LIVE_URLS). Falls back to homepage if nothing
    matches.
    """
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


# ── Simple topic detection (for KB label in prompt) ───────────
TOPIC_KEYWORDS = {
    "fees": [
        "fee", "fees", "cost", "pay", "payment", "tuition",
        "amount", "price", "ghs", "cedis", "scholarship",
        "financial", "bursary", "receipt", "billing"
    ],
    "registration": [
        "register", "registration", "admit", "admission", "apply",
        "application", "form", "portal", "login", "password",
        "student id", "matric", "entry requirement", "wassce"
    ],
    "exams": [
        "exam", "exams", "test", "quiz", "assessment", "result",
        "grade", "score", "gpa", "cgpa", "transcript", "resit",
        "repeat", "academic calendar", "semester", "timetable"
    ],
    "hostel": [
        "hostel", "accommodation", "room", "bed", "dorm",
        "dormitory", "residential", "housing", "live", "stay",
        "campus life", "dining", "meal"
    ],
    "enrollment": [
        "enroll", "enrollment", "course", "courses", "credit",
        "unit", "timetable", "schedule", "hod", "department",
        "programme", "major", "elective", "add", "drop",
        "computer science", "bsc", "bba", "ba", "engineering"
    ],
}

def detect_topic(question: str) -> str:
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


# ── Page scraper with 30-min in-memory cache ──────────────────
_page_cache: dict = {}
CACHE_TTL = 1800  # 30 minutes

def fetch_page_content(url: str) -> str:
    """Fetches, cleans, and caches a single page's text."""
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
        content = " ".join(text.split())[:3000]
        _page_cache[url] = (content, now)
        return content
    except Exception:
        return ""


def fetch_live_content(question: str) -> str:
    """
    Picks the best URLs for this specific question, fetches them,
    and returns a labelled combined string for the Gemini prompt.
    """
    urls = detect_live_urls(question)
    parts = []
    for url in urls:
        content = fetch_page_content(url)
        if content:
            parts.append(f"[Source: {url}]\n{content}")
    return "\n\n".join(parts) if parts else ""


# ── Dynamic Real-Time Context ─────────────────────────────────
def get_dynamic_context() -> str:
    """
    Builds the real-time context block injected into every prompt.
    Academic calendar dates come from Firestore (auto-refreshed
    every 6 hours) with a hardcoded fallback if Firestore is down.
    Admins update dates in Firestore — no code change needed.
    """
    now      = datetime.now(ZoneInfo("Africa/Accra"))
    day_name = now.strftime("%A")
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%B %d, %Y")
    hour     = now.hour
    weekday  = now.weekday()

    is_office_hrs = (weekday < 5) and (8 <= hour < 17)
    office_status = (
        "OPEN (Mon–Fri, 8 AM – 5 PM GMT)" if is_office_hrs else "CLOSED right now"
    )

    # Load calendar dynamically (Firestore → fallback)
    cal = get_academic_calendar()
    current_period = _detect_current_period(now, cal)

    academic_year       = cal.get("academic_year",        FALLBACK_CALENDAR["academic_year"])
    sem2_label_end      = cal.get("semester_2_label_end", FALLBACK_CALENDAR["semester_2_label_end"])
    exam2_label         = cal.get("exam_2_label",         FALLBACK_CALENDAR["exam_2_label"])

    return f"""
REAL-TIME CONTEXT (auto-injected — never ask the student for this info):
- Today's date      : {date_str} ({day_name})
- Current time (GMT): {time_str}
- Academic period   : {current_period}
- Semester 2 ends   : {sem2_label_end}
- Exam period 2     : {exam2_label}
- University offices: {office_status}
- Academic year     : {academic_year}
"""


# ── Main AI Response Function ─────────────────────────────────
def get_ai_response(question: str, knowledge_base: list, history: list) -> str:

    # 1. Detect topic (for KB label in prompt)
    topic = detect_topic(question)

    # 2. Fetch the best live page(s) for this specific question
    live_content = fetch_live_content(question)

    # 3. Real-time date/semester context (dynamic calendar)
    dynamic_context = get_dynamic_context()

    # 4. Full KB text
    kb_text = ""
    for entry in knowledge_base:
        if entry.get("active", True):
            kb_text += f"Q: {entry.get('question', '')}\nA: {entry.get('answer', '')}\n\n"

    # 5. Last 10 messages of conversation history
    history_text = ""
    for msg in history[-10:]:
        role = "Student" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('text', '')}\n"

    # 6. Build the prompt
    prompt = f"""You are ACity Bot — the official AI assistant for Academic City University College (ACity) in Accra, Ghana.

STRICT ANSWER RULES — follow in this exact order every time:

STEP 1 — KNOWLEDGE BASE FIRST (mandatory):
Search the ACITY KNOWLEDGE BASE below carefully for the answer.
If you find it, respond with that exact information directly and accurately.
Do NOT paraphrase vaguely. Do NOT say "check the website". Give the actual answer.

STEP 2 — LIVE WEBSITE CONTENT (if not in KB):
If the KB does not have the answer, check the LIVE WEBSITE CONTENT section below.
This content was freshly scraped from the official ACity website specifically for
this question. Extract the accurate answer from it.

STEP 3 — REAL-TIME CONTEXT (for date/time/semester questions):
If the question is about today's date, current semester, office hours, or exam period,
use the REAL-TIME CONTEXT block — that data is always accurate.

STEP 4 — GENERAL KNOWLEDGE (absolute last resort only):
Only if the answer is genuinely absent from ALL of the above, use your general
knowledge. Make it clear it is general information, not ACity-specific, and
direct the student to registry@acity.edu.gh for confirmation.

ALWAYS — end every single response with this line, no exceptions:
"💬 Is there anything else I can help you with regarding ACity? I'm here for questions on fees, registration, courses, exams, hostels, and more!"

OTHER RULES:
- Be warm, friendly, and concise
- Use bullet points for lists
- Never invent ACity-specific data not found in the KB or live content
- If truly unable to help, refer the student to sca@acity.edu.gh

{dynamic_context}

CONVERSATION HISTORY:
{history_text}

ACITY KNOWLEDGE BASE (topic detected: {topic}):
{kb_text}

LIVE WEBSITE CONTENT (freshly fetched for this question):
{live_content}

Student question: {question}

Answer:"""

    # 7. Try each API key in rotation
    keys = get_api_keys()
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level="minimal"
                    )
                )
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue
            raise e

    return (
        "I'm currently experiencing high demand. Please try again in a few minutes "
        "or contact registry@acity.edu.gh for urgent queries.\n\n"
        "💬 Is there anything else I can help you with regarding ACity? "
        "I'm here for questions on fees, registration, courses, exams, hostels, and more!"
    )
