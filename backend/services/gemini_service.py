import os
import pytz
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai


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


# ── Topic Detection ───────────────────────────────────────────
TOPIC_KEYWORDS = {
    "fees": ["fee","fees","cost","pay","payment","tuition","amount","price","ghs","cedis","scholarship","financial","bursary","receipt"],
    "registration": ["register","registration","admit","admission","apply","application","form","portal","login","password","student id","matric"],
    "exams": ["exam","exams","test","quiz","assessment","result","grade","score","gpa","cgpa","transcript","resit","repeat","academic calendar","semester"],
    "hostel": ["hostel","accommodation","room","bed","dorm","dormitory","residential","housing","live","stay","campus"],
    "enrollment": ["enroll","enrollment","course","courses","credit","unit","timetable","schedule","hod","department","programme","major","elective","add","drop"],
}

def detect_topic(question):
    q = question.lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return "general"


# ── Live Website Scraping ─────────────────────────────────────
TOPIC_URLS = {
    "fees": "https://acity.edu.gh/fees-scholarships/",
    "registration": "https://acity.edu.gh/admissions/",
    "exams": "https://acity.edu.gh/academics/",
    "hostel": "https://acity.edu.gh/student-life/",
    "enrollment": "https://acity.edu.gh/academics/",
    "general": "https://acity.edu.gh/",
}

def fetch_page_content(url):
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())[:3000]
    except Exception:
        return ""


# ── Dynamic Real-Time Context ─────────────────────────────────
def get_dynamic_context():
    """
    Computes live context on every request — no database needed.
    Update ACADEMIC_CALENDAR once per academic year; everything
    else (office status, current date/time) is fully automatic.
    """
    accra_tz = pytz.timezone("Africa/Accra")
    now = datetime.now(accra_tz)

    day_name = now.strftime("%A")           # e.g. "Saturday"
    time_str = now.strftime("%I:%M %p")     # e.g. "10:30 AM"
    date_str = now.strftime("%B %d, %Y")    # e.g. "March 28, 2026"
    hour = now.hour
    weekday = now.weekday()                 # 0=Monday … 6=Sunday

    # Office hours: Mon–Fri 8 AM – 5 PM GMT
    is_weekend = weekday >= 5
    is_office_hours = not is_weekend and (8 <= hour < 17)
    office_status = (
        "OPEN (Mon–Fri, 8 AM – 5 PM GMT)"
        if is_office_hours
        else "CLOSED right now"
    )

    # ── Update these dates once per academic year ─────────────
    ACADEMIC_CALENDAR = {
        "2025-2026": {
            "semester_1": {"start": "2025-09-01", "end": "2025-12-20"},
            "semester_2": {"start": "2026-01-12", "end": "2026-05-10"},
            "exam_1":     {"start": "2025-12-08", "end": "2025-12-20"},
            "exam_2":     {"start": "2026-04-27", "end": "2026-05-10"},
            "break":      {"start": "2025-12-21", "end": "2026-01-11"},
        }
    }

    current_period = _detect_current_period(now, ACADEMIC_CALENDAR["2025-2026"])

    return f"""
REAL-TIME CONTEXT (auto-injected — never ask the student for this info):
- Today's date      : {date_str} ({day_name})
- Current time (GMT): {time_str}
- Academic period   : {current_period}
- University offices: {office_status}
- Academic year     : 2025–2026
"""

def _detect_current_period(now, cal):
    today = now.date()

    def in_range(s, e):
        return (
            datetime.strptime(s, "%Y-%m-%d").date()
            <= today <=
            datetime.strptime(e, "%Y-%m-%d").date()
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

    # Build knowledge base text
    kb_text = ""
    for entry in knowledge_base:
        if entry.get("active", True):
            kb_text += f"Q: {entry.get('question', '')}\nA: {entry.get('answer', '')}\n\n"

    # Build conversation history text (last 10 messages for context)
    history_text = ""
    for msg in history[-10:]:
        role = "Student" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('text', '')}\n"

    prompt = f"""You are ACity Bot — a friendly, knowledgeable AI assistant for Academic City University College (ACity) in Accra, Ghana.

YOUR CORE BEHAVIOUR:
- You can answer ANY question a student asks — whether it is about ACity, general academic topics, study tips, career advice, or everyday knowledge.
- For ACity-specific questions (fees, registration, exams, hostel, courses), prioritise the KNOWLEDGE BASE and LIVE WEBSITE CONTENT provided below.
- For questions outside the knowledge base, use your general knowledge to give a helpful, accurate answer.
- ALWAYS end EVERY response — no exceptions — with this exact reminder on a new line:
  "💬 Is there anything else I can help you with regarding ACity? I'm here for questions on fees, registration, courses, exams, hostels, and more!"
- Be warm, concise, and encouraging. Use bullet points for lists.
- If the student asks something you genuinely cannot answer at all, say so honestly and point them to sca@acity.edu.gh for further support.

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
                contents=prompt
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
