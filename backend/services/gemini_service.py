import os
import requests
from bs4 import BeautifulSoup
from google import genai

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
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())[:3000]
    except:
        return ""

def get_ai_response(question, knowledge_base, history):
    topic = detect_topic(question)
    live_content = fetch_page_content(TOPIC_URLS.get(topic, TOPIC_URLS["general"]))

    kb_text = ""
    for entry in knowledge_base:
        if entry.get("active", True):
            kb_text += f"Q: {entry.get('question','')}\nA: {entry.get('answer','')}\n\n"

    history_text = ""
    for msg in history[-10:]:
        role = "Student" if msg.get("role") == "user" else "Assistant"
        history_text += f"{role}: {msg.get('text','')}\n"

    prompt = f"""You are the official ACity Student Assistant for Academic City University College in Ghana.

INSTRUCTIONS:
- Answer ONLY using the knowledge base below
- Be direct and specific — give exact figures, dates, and names
- Never invent information not in the knowledge base
- If you don't know, say: "Please contact the registry at registry@acity.edu.gh"
- Use bullet points for lists
- Keep answers concise

CONVERSATION HISTORY:
{history_text}

KNOWLEDGE BASE:
{kb_text}

LIVE WEBSITE CONTENT ({topic}):
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

    return "I'm currently experiencing high demand. Please try again in a few minutes or contact registry@acity.edu.gh for urgent queries."
