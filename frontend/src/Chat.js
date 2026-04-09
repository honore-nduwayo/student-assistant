import { useState, useRef, useEffect } from "react";

const RED = "#c0002a";
const DARK_RED = "#7a0019";

// ── Render plain URLs as clickable links, **bold** as bold ────
function renderInlineLinks(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  return parts.map((part, i) => {
    if (part.match(/^https?:\/\//)) {
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noreferrer"
          style={{ color: RED, textDecoration: "underline", wordBreak: "break-all" }}
        >
          {part}
        </a>
      );
    }
    const boldParts = part.split(/\*\*(.*?)\*\*/g);
    return boldParts.map((bp, j) =>
      j % 2 === 1 ? (
        <strong key={`${i}-${j}`} style={{ color: RED }}>
          {bp}
        </strong>
      ) : (
        bp
      )
    );
  });
}

// ── Render a single message — steps get numbered badges ───────
function renderText(text) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    if (!line.trim()) return <br key={i} />;

    // "Step 1:" / "Step 1." patterns
    const stepMatch = line.trim().match(/^(Step\s*\d+[:.]?)\s*/i);
    if (stepMatch) {
      const num = stepMatch[0].replace(/[^0-9]/g, "");
      const rest = line.trim().slice(stepMatch[0].length);
      return (
        <div
          key={i}
          style={{ display: "flex", gap: "8px", marginBottom: "7px", alignItems: "flex-start" }}
        >
          <span
            style={{
              color: "#fff",
              background: RED,
              fontWeight: "700",
              fontSize: "11px",
              borderRadius: "50%",
              minWidth: "22px",
              height: "22px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              marginTop: "2px",
            }}
          >
            {num}
          </span>
          <span>{renderInlineLinks(rest)}</span>
        </div>
      );
    }

    // Bullet points "* " or "- "
    if (line.trim().startsWith("* ") || line.trim().startsWith("- ")) {
      return (
        <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
          <span style={{ color: RED, fontWeight: "bold", flexShrink: 0 }}>•</span>
          <span>{renderInlineLinks(line.trim().slice(2))}</span>
        </div>
      );
    }

    // Numbered list "1." "2." (not "Step N:")
    if (/^\d+\./.test(line.trim())) {
      const num = line.trim().match(/^\d+/)[0];
      return (
        <div key={i} style={{ display: "flex", gap: "8px", marginBottom: "4px" }}>
          <span
            style={{ color: RED, fontWeight: "bold", minWidth: "20px", flexShrink: 0 }}
          >
            {num}.
          </span>
          <span>{renderInlineLinks(line.trim().replace(/^\d+\.\s*/, ""))}</span>
        </div>
      );
    }

    return (
      <div key={i} style={{ marginBottom: "4px" }}>
        {renderInlineLinks(line)}
      </div>
    );
  });
}

// ── Full pool of 25 suggested questions ───────────────────────
const ALL_SUGGESTED_QUESTIONS = [
  { label: "Pay Fees",         q: "How do I pay my tuition fees?" },
  { label: "Entry Requirements", q: "What are the entry requirements at ACity?" },
  { label: "Register Courses", q: "How do I register for courses?" },
  { label: "Semester Dates",   q: "When does Semester 2 end?" },
  { label: "Exam Results",     q: "How do I check my exam results?" },
  { label: "Scholarships",     q: "Are there scholarships available at ACity?" },
  { label: "How to Apply",     q: "How do I apply to Academic City?" },
  { label: "Programmes",       q: "What programmes does ACity offer?" },
  { label: "Hostel",           q: "How do I apply for a hostel room?" },
  { label: "CS Fees",          q: "What is the tuition fee for Computer Science?" },
  { label: "Change Course",    q: "How do I change my course or major?" },
  { label: "Graduation",       q: "When is the next graduation ceremony?" },
  { label: "Get Transcript",   q: "How do I get my official transcript?" },
  { label: "Payment Methods",  q: "What are the accepted payment methods?" },
  { label: "Masters",          q: "Does ACity offer Masters programmes?" },
  { label: "Contact Registry", q: "How do I contact the Registry?" },
  { label: "Student Clubs",    q: "What clubs can I join at ACity?" },
  { label: "Portal Password",  q: "How do I reset my ACity portal password?" },
  { label: "Resit Exams",      q: "What are the exam resit procedures?" },
  { label: "Accreditation",    q: "Is ACity accredited by NAB?" },
  { label: "Academic Calendar", q: "What is the academic calendar for this year?" },
  { label: "Defer Admission",  q: "How do I defer my admission?" },
  { label: "Location",         q: "Where is ACity located?" },
  { label: "Engineering",      q: "What engineering programmes does ACity offer?" },
  { label: "Hostel Fees",      q: "How much does hostel accommodation cost?" },
];

function getRandomQuestions(pool, n = 4) {
  return [...pool].sort(() => Math.random() - 0.5).slice(0, n);
}

// ── CSS animations ─────────────────────────────────────────────
const css = `
  @keyframes breathe { 0%,100%{box-shadow:0 0 0 0 rgba(74,222,128,0.5)} 60%{box-shadow:0 0 0 8px rgba(74,222,128,0)} }
  @keyframes sendGlow { 0%,100%{box-shadow:0 6px 20px rgba(192,0,42,0.4)} 50%{box-shadow:0 6px 30px rgba(192,0,42,0.7)} }
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  .online-dot { animation: breathe 2.5s infinite; }
  .send-btn-chat { animation: sendGlow 2.5s infinite; transition: transform 0.2s ease !important; }
  .send-btn-chat:hover { transform: scale(1.12) rotate(15deg) !important; }
  .chip-btn { transition: all 0.25s ease !important; }
  .chip-btn:hover { background: linear-gradient(135deg,#c0002a,#7a0019) !important; color: #fff !important; border-color: transparent !important; box-shadow: 0 4px 12px rgba(192,0,42,0.35) !important; transform: translateY(-1px) !important; }
  .msg-anim { animation: fadeUp 0.35s ease both; }
  .nav-side { transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important; border-left: 3px solid transparent !important; }
  .nav-side:hover { background: rgba(255,255,255,0.15) !important; border-left-color: rgba(255,255,255,0.5) !important; padding-left: 20px !important; color: #fff !important; }
  .feedback-up { transition: all 0.2s ease; }
  .feedback-up:hover { background: #dcfce7 !important; border-color: #4ade80 !important; transform: scale(1.1); }
  .feedback-down { transition: all 0.2s ease; }
  .feedback-down:hover { background: #fee2e2 !important; border-color: #f87171 !important; transform: scale(1.1); }
`;

export default function Chat() {
  // Kai's intro message — matches backend identity
  const [messages, setMessages] = useState([
    {
      role: "bot",
      text:
        "👋 Hi there! I'm **Kai**, your ACity student assistant!\n\nI can help you with:\n* 💰 Fees & scholarships\n* 📝 Registration & admissions\n* 📚 Courses & enrollment\n* 📅 Exams & results\n* 🏠 Hostel & campus life\n* 🎓 Graduation procedures\n\nWhat would you like to know today?",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [ratings, setRatings] = useState({});

  // 4 random questions from the pool — refreshed after every bot reply
  const [suggestedQuestions, setSuggestedQuestions] = useState(
    () => getRandomQuestions(ALL_SUGGESTED_QUESTIONS, 4)
  );

  const bottomRef = useRef(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const h = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendFeedback = async (messageId, rating, question, answer) => {
    setRatings((prev) => ({ ...prev, [messageId]: rating }));
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: messageId, rating, question, answer }),
      });
    } catch {}
  };

  const sendMessage = async (text) => {
    const question = (text || input).trim();
    if (!question) return;
    setInput("");
    if (isMobile) setSidebarOpen(false);
    const newMessages = [...messages, { role: "user", text: question }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, history: newMessages.slice(-10) }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "bot", text: data.answer }]);
      // Refresh suggested questions after every bot reply
      setSuggestedQuestions(getRandomQuestions(ALL_SUGGESTED_QUESTIONS, 4));
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          // Error message mirrors backend's Kai closing line exactly
          text: "Sorry, I couldn't connect to the server. Please try again or contact registry@acity.edu.gh.\n\n💬 Anything else I can help with? I'm Kai — always here for questions on fees, registration, courses, exams, hostels, and more!",
        },
      ]);
    }
    setLoading(false);
  };

  return (
    <div style={s.page}>
      <style>{css}</style>

      {isMobile && sidebarOpen && (
        <div onClick={() => setSidebarOpen(false)} style={s.overlay} />
      )}

      {/* ── Sidebar ── */}
      <div
        style={
          isMobile
            ? {
                position: "fixed",
                top: 0, left: 0,
                width: "220px",
                height: "100dvh",
                zIndex: 300,
                transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)",
                transition: "transform 0.3s cubic-bezier(0.4,0,0.2,1)",
              }
            : {
                width: sidebarOpen ? "220px" : "0px",
                flexShrink: 0,
                overflow: "hidden",
                transition: "width 0.35s cubic-bezier(0.4,0,0.2,1)",
              }
        }
      >
        <div style={s.sidebarInner}>
          <div style={s.sidebarHeader}>
            <img
              src="/logo.png"
              alt="ACity"
              style={s.sidebarLogo}
              onError={(e) => { e.target.style.display = "none"; }}
            />
            <div>
              <div style={{ color: "#fff", fontWeight: "700", fontSize: "13px", letterSpacing: "0.3px" }}>
                Kai
              </div>
              <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "10px" }}>
                ACity Student Assistant
              </div>
            </div>
            {isMobile && (
              <button onClick={() => setSidebarOpen(false)} style={s.closeBtn}>✕</button>
            )}
          </div>

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.12)", paddingTop: "14px" }}>
            <div style={s.topicLabel}>Quick Topics</div>
            {/* Sidebar also shows the same dynamic 4 suggestions */}
            {suggestedQuestions.map((t, i) => (
              <button
                key={i}
                className="nav-side"
                onClick={() => sendMessage(t.q)}
                style={s.topicBtn}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div style={s.sidebarFooter}>
            <div style={{ color: "rgba(255,255,255,0.35)", fontSize: "10px" }}>Powered by AI</div>
            <div style={{ color: "rgba(255,255,255,0.35)", fontSize: "10px" }}>Kai for ACity</div>
          </div>
        </div>
      </div>

      {/* ── Main panel ── */}
      <div style={s.main}>

        {/* Header */}
        <div style={s.header}>
          <div style={s.headerDecor1} />
          <div style={s.headerDecor2} />
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={s.hamburger}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <div style={s.headerLogoWrap}>
            <img
              src="/logochat.png"
              alt="Kai"
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              onError={(e) => { e.target.style.display = "none"; }}
            />
          </div>
          <div style={s.headerInfo}>
            <div style={s.headerTitle}>Kai — ACity Student Assistant</div>
            <div style={s.headerSub}>
              <span className="online-dot" style={s.dot} />
              Online · Academic City University College
            </div>
          </div>
        </div>

        {/* Messages */}
        <div style={s.messages}>
          {messages.map((msg, i) => (
            <div
              key={i}
              className="msg-anim"
              style={msg.role === "user" ? s.userRow : s.botRow}
            >
              {msg.role === "bot" && (
                <div style={s.avatar}>
                  <img
                    src="/logochat.png"
                    alt="Kai"
                    style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    onError={(e) => { e.target.style.display = "none"; }}
                  />
                </div>
              )}
              <div style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                maxWidth: msg.role === "user" ? "70%" : "83%",
              }}>
                <div style={msg.role === "user" ? s.userBubble : s.botBubble}>
                  {renderText(msg.text)}
                </div>
                {/* Thumbs up/down — only on Kai's replies after the first */}
                {msg.role === "bot" && i > 0 && (
                  <div style={{ display: "flex", gap: "6px", paddingLeft: "4px", alignItems: "center" }}>
                    <button
                      className="feedback-up"
                      onClick={() =>
                        sendFeedback(`msg_${i}`, "up", messages[i - 1]?.text || "", msg.text)
                      }
                      style={{
                        ...s.feedbackBtn,
                        background: ratings[`msg_${i}`] === "up" ? "#4ade80" : "#f0fdf4",
                        border: `1.5px solid ${ratings[`msg_${i}`] === "up" ? "#4ade80" : "#86efac"}`,
                      }}
                    >
                      👍
                    </button>
                    <button
                      className="feedback-down"
                      onClick={() =>
                        sendFeedback(`msg_${i}`, "down", messages[i - 1]?.text || "", msg.text)
                      }
                      style={{
                        ...s.feedbackBtn,
                        background: ratings[`msg_${i}`] === "down" ? "#f87171" : "#fef2f2",
                        border: `1.5px solid ${ratings[`msg_${i}`] === "down" ? "#f87171" : "#fca5a5"}`,
                      }}
                    >
                      👎
                    </button>
                    {ratings[`msg_${i}`] && (
                      <span style={{ fontSize: "10px", color: "#aaa" }}>Thanks!</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div style={s.botRow}>
              <div style={s.avatar}>
                <img
                  src="/logochat.png"
                  alt="Kai"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                  onError={(e) => { e.target.style.display = "none"; }}
                />
              </div>
              <div style={{ ...s.botBubble, color: "#bbb", fontStyle: "italic" }}>
                Kai is thinking...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Dynamic suggestion chips — 4 random, refresh after each answer */}
        <div style={s.chips}>
          {suggestedQuestions.map((t, i) => (
            <button
              key={i}
              className="chip-btn"
              onClick={() => sendMessage(t.q)}
              style={s.chip}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Input bar */}
        <div style={s.inputArea}>
          <textarea
            style={s.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Ask Kai anything about ACity..."
            rows={2}
          />
          <button
            className="send-btn-chat"
            style={s.sendBtn}
            onClick={() => sendMessage()}
            disabled={loading}
          >
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>

        <div style={s.footer}>Kai · Powered by AI · Official ACity information only</div>
      </div>
    </div>
  );
}

const s = {
  page: { display: "flex", width: "100vw", height: "100dvh", background: "#fafafa", fontFamily: "-apple-system,'Segoe UI',sans-serif", overflow: "hidden", position: "relative" },
  overlay: { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 299, backdropFilter: "blur(2px)" },
  sidebarInner: { width: "220px", height: "100%", display: "flex", flexDirection: "column", padding: "20px 12px", boxSizing: "border-box", background: `linear-gradient(180deg,${RED} 0%,${DARK_RED} 100%)` },
  sidebarHeader: { display: "flex", alignItems: "center", gap: "10px", marginBottom: "18px" },
  sidebarLogo: { width: "38px", height: "38px", objectFit: "contain", background: "#fff", borderRadius: "10px", padding: "4px", flexShrink: 0, boxShadow: "0 3px 10px rgba(0,0,0,0.2)" },
  closeBtn: { background: "transparent", border: "none", color: "rgba(255,255,255,0.6)", fontSize: "16px", cursor: "pointer", marginLeft: "auto", padding: "4px", borderRadius: "6px" },
  topicLabel: { color: "rgba(255,255,255,0.4)", fontSize: "9px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "1.5px", marginBottom: "8px", paddingLeft: "14px" },
  topicBtn: { display: "block", width: "100%", background: "transparent", border: "none", borderLeft: "3px solid transparent", borderRadius: "0 10px 10px 0", color: "rgba(255,255,255,0.65)", padding: "10px 14px", cursor: "pointer", textAlign: "left", fontSize: "13px", fontWeight: "500", marginBottom: "2px", letterSpacing: "0.2px" },
  sidebarFooter: { marginTop: "auto", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px" },
  main: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 },
  header: { background: `linear-gradient(135deg,${RED} 0%,${DARK_RED} 100%)`, color: "#fff", padding: "14px 18px", display: "flex", alignItems: "center", gap: "12px", flexShrink: 0, position: "relative", overflow: "hidden" },
  headerDecor1: { position: "absolute", top: "-30px", right: "-20px", width: "100px", height: "100px", background: "rgba(255,255,255,0.06)", borderRadius: "50%", pointerEvents: "none" },
  headerDecor2: { position: "absolute", bottom: "-40px", left: "30%", width: "80px", height: "80px", background: "rgba(255,255,255,0.04)", borderRadius: "50%", pointerEvents: "none" },
  hamburger: { background: "transparent", border: "none", cursor: "pointer", padding: "4px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, borderRadius: "8px", zIndex: 1 },
  headerLogoWrap: { width: "42px", height: "42px", background: "#fff", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, boxShadow: "0 3px 12px rgba(0,0,0,0.25)", zIndex: 1, overflow: "hidden" },
  headerInfo: { flex: 1, minWidth: 0, zIndex: 1 },
  headerTitle: { fontWeight: "700", fontSize: "15px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", letterSpacing: "0.3px" },
  headerSub: { fontSize: "11px", opacity: 0.75, display: "flex", alignItems: "center", gap: "6px", marginTop: "3px" },
  dot: { width: "7px", height: "7px", borderRadius: "50%", background: "#4ade80", display: "inline-block", flexShrink: 0 },
  messages: { flex: 1, overflowY: "auto", padding: "20px 16px", display: "flex", flexDirection: "column", gap: "16px", background: "linear-gradient(180deg,#fff9fa 0%,#fff 100%)" },
  botRow: { display: "flex", alignItems: "flex-start", gap: "10px" },
  userRow: { display: "flex", justifyContent: "flex-end" },
  avatar: { width: "34px", height: "34px", background: `linear-gradient(135deg,${RED},${DARK_RED})`, borderRadius: "50%", overflow: "hidden", flexShrink: 0, boxShadow: `0 3px 10px rgba(192,0,42,0.4)` },
  botBubble: { background: "#fff", borderRadius: "2px 18px 18px 18px", padding: "12px 16px", fontSize: "14px", lineHeight: "1.7", border: "1px solid rgba(192,0,42,0.1)", color: "#1a1a1a", boxShadow: "0 3px 12px rgba(0,0,0,0.06)" },
  userBubble: { background: `linear-gradient(135deg,${RED},${DARK_RED})`, color: "#fff", borderRadius: "18px 2px 18px 18px", padding: "12px 16px", fontSize: "14px", lineHeight: "1.7", boxShadow: "0 4px 14px rgba(192,0,42,0.3)" },
  feedbackBtn: { border: "none", borderRadius: "20px", padding: "4px 10px", fontSize: "14px", cursor: "pointer", transition: "all 0.2s" },
  chips: { padding: "8px 14px 6px", background: "#fff", borderTop: "1px solid rgba(192,0,42,0.08)", display: "flex", gap: "6px", flexWrap: "wrap", flexShrink: 0 },
  chip: { background: "#fff5f5", border: "1.5px solid rgba(192,0,42,0.2)", borderRadius: "25px", padding: "5px 15px", fontSize: "12px", color: RED, cursor: "pointer", fontWeight: "600", letterSpacing: "0.2px" },
  inputArea: { display: "flex", padding: "10px 14px 12px", borderTop: "1px solid rgba(192,0,42,0.08)", gap: "10px", background: "#fff", alignItems: "center", flexShrink: 0 },
  input: { flex: 1, background: "#fff8f9", border: `2px solid rgba(192,0,42,0.15)`, borderRadius: "28px", padding: "10px 18px", fontSize: "14px", resize: "none", outline: "none", fontFamily: "inherit", color: "#1a1a1a", lineHeight: "1.5", boxShadow: "inset 0 2px 4px rgba(192,0,42,0.04)" },
  sendBtn: { background: `linear-gradient(135deg,${RED},${DARK_RED})`, color: "#fff", border: "none", borderRadius: "50%", width: "46px", height: "46px", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 },
  footer: { textAlign: "center", fontSize: "11px", color: "#ccc", padding: "5px", background: "#fff", flexShrink: 0, letterSpacing: "0.3px" },
};
