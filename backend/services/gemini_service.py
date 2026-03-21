import os
import requests
from bs4 import BeautifulSoup
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TOPIC_URL_MAP = {
    "fees":         "https://acity.edu.gh/fees-scholarships/",
    "registration": "https://acity.edu.gh/registry/",
    "enrollment":   "https://acity.edu.gh/undergraduate-programmes/",
    "exams":        "https://acity.edu.gh/registry/",
    "hostel":       "https://acity.edu.gh/fees-scholarships/",
    "general":      "https://acity.edu.gh/about/",
}

def fetch_page_content(url, max_chars=3000):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (ACity Student Assistant)"}
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:max_chars]
    except Exception:
        return ""

def detect_topic(question):
    q = question.lower()
    if any(w in q for w in ["fee", "pay", "cost", "ghs", "usd", "scholarship", "installment"]):
        return "fees"
    if any(w in q for w in ["register", "registration", "portal", "deadline", "cohort"]):
        return "registration"
    if any(w in q for w in ["enroll", "course", "timetable", "add", "drop", "programme", "major", "change"]):
        return "enrollment"
    if any(w in q for w in ["exam", "result", "grade", "resit", "revision", "graduation"]):
        return "exams"
    if any(w in q for w in ["hostel", "accommodation", "room", "housing"]):
        return "hostel"
    return None

def get_ai_response(question, knowledge_base, history=[]):
    # Build knowledge base context
    kb_context = "\n\n".join([
        f"Q: {item['question']}\nA: {item['answer']}"
        for item in knowledge_base
    ])

    # Try to fetch live page for extra context
    live_section = ""
    live_url = ""
    topic = detect_topic(question)
    if topic and topic in TOPIC_URL_MAP:
        live_url = TOPIC_URL_MAP[topic]
        live_content = fetch_page_content(live_url)
        if live_content:
            live_section = f"\nLIVE WEBSITE CONTENT (from {live_url}):\n{live_content}\n"

    # Build conversation history string
    history_text = ""
    if history:
        history_text = "\nCONVERSATION HISTORY (for context):\n"
        for msg in history[-6:]:  # last 6 messages max
            role = "Student" if msg["role"] == "user" else "Assistant"
            history_text += f"{role}: {msg['text']}\n"
        history_text += "\n"

    prompt = f"""You are an expert Student Assistant for Academic City University College (ACity), Ghana.
You have deep knowledge of ACity's programmes, fees, registration, exams, hostel, and policies.

IMPORTANT RULES:
1. Give DIRECT, SPECIFIC answers — students want facts immediately, not vague redirects
2. Use the conversation history to understand follow-up questions (e.g. if they asked about CS fees before, "what about AI?" means AI fees)
3. Format responses clearly:
   - Use bullet points for lists
   - Use bold for important numbers/dates
   - Make links appear on their own line
4. For fees, ALWAYS state the exact GHS and USD amounts from the knowledge base
5. For programme changes, explain the exact process step by step
6. Only say "I don't have that information" if it's truly not in the knowledge base
7. Never make up fees, dates, or policies
8. Keep answers concise but complete — no unnecessary filler text

ACADEMIC CITY KNOWLEDGE BASE:
{kb_context}
{live_section}{history_text}
CURRENT STUDENT QUESTION: {question}

Answer (be specific, use real data from the knowledge base):"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    answer = response.text.strip()
    if live_url and live_url not in answer:
        answer += f"\n\nMore info: {live_url}"
    return answer
