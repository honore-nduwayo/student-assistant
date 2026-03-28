import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
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


# ── Topic Detection (used for website scraping only) ──────────
TOPIC_KEYWORDS = {
    "fees": ["fee","fees","cost","pay","payment","tuition","amount","price","ghs","cedis","scholarship","financial","bursary","receipt"],
    "registration": ["register","registration","admit","admission","apply","application","form","portal","login","password","student id","matric"],
    "exams": ["exam","exams","test","quiz","assessment","result","grade","score","gpa","cgpa","transcript","resit","repeat","academic calendar","semester"],
    "hostel": ["hostel","accommodation","room","bed","dorm","dormitory","residential","housing","live","stay","campus"],
    "enrollment": ["enroll","enrollment","course","courses","credit","unit","timetable","schedule","hod","department","programme","major","elective","add","drop","computer science","bsc","bba","ba"],
}

def detect_topic(question):
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


# ── Live Website Scraping with 30-min Cache ───────────────────
TOPIC_URLS = {
    "fees": "https://acity.edu.gh/fees-scholarships/",
    "registration": "https://acity.edu.gh/admissions/",
    "exams": "https://acity.edu.gh/academics/",
    "hostel": "https://acity.edu.gh/student-life/",
    "enrollment": "https://acity.edu.gh/academics/",
    "general": "https://acity.edu.gh/",
}

_page_cache = {}
CACHE_TTL = 1800  # 30 minutes in seconds

def fetch_page_content(url):
    now = time.time()
    if url in _page_cache:
        content, cached_at = _page_cache[url]
        if now - cached_at < CACHE_TTL:
            return content
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        content = " ".join(text.split())[:3000]
        _page_cache[url] = (content, now)
        return content
    except Exception:
        return ""


# ── Dynamic Real-Time Context ─────────────────────────────────
def get_dynamic_context():
    now = datetime.now(ZoneInfo("Africa/Accra"))

    day_name = now.strftime("%A")
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%B %d, %Y")
    hour = now.hour
    weekday = now.weekday()

    is_weekend = weekday >= 5
    is_office_hours = not is_weekend and (8 <= hour < 17)
    office_status = (
        "OPEN (Mon–Fri, 8 AM – 5 PM GMT)"
        if is_office_hours
        else "CLOSED right now"
    )

    # ── Update this block once per academic year only ─────────
    ACADEMIC_CALENDAR = {
        "semester_1": {"start": "2025-09-01", "end": "2025-12-20"},
        "semester_2": {"start": "2026-01-12", "end": "2026-05-10"},
        "exam_1":     {"start": "2025-12-08", "end": "2025-12-20"},
        "exam_2":     {"start": "2026-04-27", "end": "2026-05-10"},
        "break":      {"start": "2025-12-21", "end": "2026-01-11"},
    }

    current_period = _detect_current_period(now, ACADEMIC_CALENDAR)

    return f"""
REAL-TIME CONTEXT (auto-injected — never ask the student for this info):
- Today's date      : {date_str} ({day_name})
- Current time (GMT): {time_str}
- Academic period   : {current_period}
- Semester 2 ends   : May 10, 2026
- Exam period 2     : April 27 – May 10, 2026
- University offices: {office_status}
- Academic year     : 2025–2026
"""

def _detect_current_period(now, cal):
    today = now.date()

    def in_range(start, end):
        return (
            datetime.strptime(start, "%Y-%m-%d").date()
            <= today <=
            datetime.strptime(end, "%Y-%m-%d").date()
        )

    if in_range(**cal["exam_1"]):
        return "Semester 1 Examination Period"
    if in_range(**cal["exam_2"]):
        return "Semester 2 Examination Period"
    if in_range(**cal["semester_1"]):
        return "Semester 1 (classes in session)"
    if in_range(**cal["semester_2"]):
        return "Semester 2 (classes in session)"
    if in_range(**cal["break"]):
        return "Semester Break / Vacation"
    return "Pre-semester / Registration Period"


# ── Main AI Response Function ─────────────────────────────────
def get_ai_response(question, knowledge_base, history):
    topic = detect_topic(question)
    live_content = fetch_page_content(TOPIC_URLS.get(topic, TOPIC_URLS["general"]))
    dynamic_context = get_dynamic_context()

    # ── Send the FULL knowledge base — no topic filter, no cap ─
    # Filtering and capping were hiding answers from Gemini.
    # Gemini 2.5 Flash handles large context windows efficiently.
    kb_text = ""
    for entry in knowledge_base:
        if entry.get("active", True):
            kb_text += f"Q: {entry.get('question', '')}\nA: {entry.get('answer', '')}\n\n"

    # Build conversation history (last 10 messages)
    history_text = ""
    for msg in history[-10:]:
        role = "Student" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('text', '')}\n"

    prompt = f"""You are ACity Bot — a friendly AI assistant for Academic City University College (ACity) in Accra, Ghana.

PRIORITY RULES — follow in this exact order:
1. ALWAYS check the ACITY KNOWLEDGE BASE below first. If the answer is there, use it directly and accurately. Do not summarise or rephrase it into vague advice — give the actual answer.
2. If the answer is NOT in the knowledge base, check the REAL-TIME CONTEXT for date/time/semester facts and answer from that.
3. If the answer is in neither, use your general knowledge to give a helpful response.
4. NEVER tell a student to "check the website" or "contact the registry" for something that is already answered in the knowledge base below.
5. ALWAYS end every single response — no exceptions — with this line:
   "💬 Is there anything else I can help you with regarding ACity? I'm here for questions on fees, registration, courses, exams, hostels, and more!"

{dynamic_context}

CONVERSATION HISTORY:
{history_text}

ACITY KNOWLEDGE BASE:
{kb_text}

LIVE WEBSITE CONTENT (topic: {topic}):
{live_content}

Student question: {question}

Answer:"""

    keys = get_api_keys()
    for key in keys:
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0  # Thinking OFF for speed
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
