import { useState, useRef, useEffect } from "react";

const RED = "#c0002a";
const DARK_RED = "#7a0019";

function renderInlineLinks(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  return parts.map((part, i) => {
    if (part.match(/^https?:\/\//)) {
      return (<a key={i} href={part} target="_blank" rel="noreferrer" style={{ color:RED, textDecoration:"underline", wordBreak:"break-all" }}>{part}</a>);
    }
    const boldParts = part.split(/\*\*(.*?)\*\*/g);
    return boldParts.map((bp, j) => j % 2 === 1 ? <strong key={`${i}-${j}`} style={{ color:RED }}>{bp}</strong> : bp);
  });
}

function renderText(text) {
  const lines = text.split("\n");
  return lines.map((line, i) => {
    if (!line.trim()) return <br key={i} />;
    if (line.trim().startsWith("* ") || line.trim().startsWith("- ")) {
      return (<div key={i} style={{ display:"flex", gap:"8px", marginBottom:"4px" }}><span style={{ color:RED, fontWeight:"bold", flexShrink:0 }}>•</span><span>{renderInlineLinks(line.trim().slice(2))}</span></div>);
    }
    if (/^\d+\./.test(line.trim())) {
      const num = line.trim().match(/^\d+/)[0];
      return (<div key={i} style={{ display:"flex", gap:"8px", marginBottom:"4px" }}><span style={{ color:RED, fontWeight:"bold", minWidth:"20px", flexShrink:0 }}>{num}.</span><span>{renderInlineLinks(line.trim().replace(/^\d+\.\s*/,""))}</span></div>);
    }
    return (<div key={i} style={{ marginBottom:"4px" }}>{renderInlineLinks(line)}</div>);
  });
}

const TOPICS = [
  { label:"Fees", q:"What are the tuition fees at ACity?" },
  { label:"Registration", q:"How do I register for courses?" },
  { label:"Exams", q:"When do Semester 1 exams start?" },
  { label:"Hostel", q:"How do I apply for hostel?" },
  { label:"Enrollment", q:"How do I enroll in courses?" },
  { label:"Programmes", q:"What programmes does ACity offer?" },
  { label:"Scholarships", q:"What scholarships are available at ACity?" },
  { label:"Contact", q:"What are the contact details for ACity?" },
];

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
  const [messages, setMessages] = useState([{ role:"bot", text:"👋 Welcome! I'm the **ACity Student Assistant**.\n\nI can help you with:\n* Registration & academic calendar\n* Fees & payment methods\n* Course enrollment\n* Exams & results\n* Hostel & accommodation\n\nWhat would you like to know?" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [ratings, setRatings] = useState({});
  const bottomRef = useRef(null);
  const isMobile = window.innerWidth <= 768;

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  const sendFeedback = async (messageId, rating, question, answer) => {
    setRatings(prev => ({ ...prev, [messageId]: rating }));
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/feedback`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ message_id:messageId, rating, question, answer })
      });
    } catch {}
  };

  const sendMessage = async (text) => {
    const question = (text || input).trim();
    if (!question) return;
    setInput("");
    if (isMobile) setSidebarOpen(false);
    const newMessages = [...messages, { role:"user", text:question }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL}/ask`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ question, history:newMessages.slice(-10) })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role:"bot", text:data.answer }]);
    } catch {
      setMessages(prev => [...prev, { role:"bot", text:"Sorry, I could not connect to the server. Please try again.\n\nFor urgent queries contact: registry@acity.edu.gh" }]);
    }
    setLoading(false);
  };

  return (
    <div style={s.page}>
      <style>{css}</style>

      {isMobile && sidebarOpen && (
        <div onClick={() => setSidebarOpen(false)} style={s.overlay} />
      )}

      {/* Sidebar */}
      <div style={{
        ...s.sidebar,
        transform: sidebarOpen ? "translateX(0)" : "translateX(-100%)",
        position: isMobile ? "fixed" : "absolute",
        zIndex: isMobile ? 300 : 200,
        height: "100%",
        flexShrink: 0,
      }}>
        <div style={s.sidebarInner}>
          <div style={s.sidebarHeader}>
            <img src="/logo.png" alt="ACity" style={s.sidebarLogo} onError={e=>{e.target.style.display="none"}} />
            <div>
              <div style={{ color:"#fff", fontWeight:"700", fontSize:"13px", letterSpacing:"0.3px" }}>ACity</div>
              <div style={{ color:"rgba(255,255,255,0.5)", fontSize:"10px" }}>Student Assistant</div>
            </div>
            {isMobile && (
              <button onClick={() => setSidebarOpen(false)} style={s.closeBtn}>✕</button>
            )}
          </div>

          <div style={{ borderTop:"1px solid rgba(255,255,255,0.12)", paddingTop:"14px" }}>
            <div style={s.topicLabel}>Quick Topics</div>
            {TOPICS.map((t, i) => (
              <button key={i} className="nav-side" onClick={() => sendMessage(t.q)} style={s.topicBtn}>{t.label}</button>
            ))}
          </div>

          <div style={s.sidebarFooter}>
            <div style={{ color:"rgba(255,255,255,0.35)", fontSize:"10px" }}>Powered by AI</div>
            <div style={{ color:"rgba(255,255,255,0.35)", fontSize:"10px" }}>Official ACity info only</div>
          </div>
        </div>
      </div>

      {/* Main */}
      <div style={s.main}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.headerDecor1} />
          <div style={s.headerDecor2} />
          <button onClick={() => setSidebarOpen(!sidebarOpen)} style={s.hamburger}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div style={s.headerLogoWrap}>
            <img src="/logo.png" alt="ACity" style={s.headerLogo} onError={e=>{e.target.style.display="none"}} />
          </div>
          <div style={s.headerInfo}>
            <div style={s.headerTitle}>ACity Student Assistant</div>
            <div style={s.headerSub}>
              <span className="online-dot" style={s.dot} />
              Online · Academic City University College
            </div>
          </div>
        </div>

        {/* Messages */}
        <div style={s.messages}>
          {messages.map((msg, i) => (
            <div key={i} className="msg-anim" style={msg.role==="user" ? s.userRow : s.botRow}>
              {msg.role==="bot" && (
                <div style={s.avatar}>
                  <img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} />
                </div>
              )}
              <div style={{ display:"flex", flexDirection:"column", gap:"6px", maxWidth: msg.role==="user" ? "70%" : "83%" }}>
                <div style={msg.role==="user" ? s.userBubble : s.botBubble}>
                  {renderText(msg.text)}
                </div>
                {msg.role==="bot" && i > 0 && (
                  <div style={{ display:"flex", gap:"6px", paddingLeft:"4px", alignItems:"center" }}>
                    <button
                      className="feedback-up"
                      onClick={() => sendFeedback(`msg_${i}`, "up", messages[i-1]?.text||"", msg.text)}
                      style={{ ...s.feedbackBtn, background: ratings[`msg_${i}`]==="up" ? "#4ade80" : "#f0fdf4", border: `1.5px solid ${ratings[`msg_${i}`]==="up" ? "#4ade80" : "#86efac"}` }}
                    >👍</button>
                    <button
                      className="feedback-down"
                      onClick={() => sendFeedback(`msg_${i}`, "down", messages[i-1]?.text||"", msg.text)}
                      style={{ ...s.feedbackBtn, background: ratings[`msg_${i}`]==="down" ? "#f87171" : "#fef2f2", border: `1.5px solid ${ratings[`msg_${i}`]==="down" ? "#f87171" : "#fca5a5"}` }}
                    >👎</button>
                    {ratings[`msg_${i}`] && <span style={{ fontSize:"10px", color:"#aaa" }}>Thanks!</span>}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div style={s.botRow}>
              <div style={s.avatar}>
                <img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} />
              </div>
              <div style={{...s.botBubble, color:"#bbb", fontStyle:"italic"}}>Thinking...</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Topic chips */}
        <div style={s.chips}>
          {TOPICS.slice(0,4).map((t,i) => (
            <button key={i} className="chip-btn" onClick={() => sendMessage(t.q)} style={s.chip}>{t.label}</button>
          ))}
        </div>

        {/* Input */}
        <div style={s.inputArea}>
          <textarea
            style={s.input}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); sendMessage(); }}}
            placeholder="Ask a question about ACity..."
            rows={2}
          />
          <button className="send-btn-chat" style={s.sendBtn} onClick={() => sendMessage()} disabled={loading}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
        <div style={s.footer}>Powered by AI · Official ACity information only</div>
      </div>
    </div>
  );
}

const s = {
  page:{ display:"flex", width:"100vw", height:"100dvh", background:"#fafafa", fontFamily:"-apple-system,'Segoe UI',sans-serif", overflow:"hidden", position:"relative", overscrollBehavior:"none" },
  overlay:{ position:"fixed", inset:0, background:"rgba(0,0,0,0.55)", zIndex:299, backdropFilter:"blur(2px)" },
  sidebar:{ width:"220px", background:`linear-gradient(180deg,${RED} 0%,${DARK_RED} 100%)`, transition:"transform 0.3s cubic-bezier(0.4,0,0.2,1)", top:0, left:0 },
  sidebarInner:{ width:"220px", height:"100%", display:"flex", flexDirection:"column", padding:"20px 12px", boxSizing:"border-box" },
  sidebarHeader:{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"18px" },
  sidebarLogo:{ width:"38px", height:"38px", objectFit:"contain", background:"#fff", borderRadius:"10px", padding:"4px", flexShrink:0, boxShadow:"0 3px 10px rgba(0,0,0,0.2)" },
  closeBtn:{ background:"transparent", border:"none", color:"rgba(255,255,255,0.6)", fontSize:"16px", cursor:"pointer", marginLeft:"auto", padding:"4px", borderRadius:"6px" },
  topicLabel:{ color:"rgba(255,255,255,0.4)", fontSize:"9px", fontWeight:"800", textTransform:"uppercase", letterSpacing:"1.5px", marginBottom:"8px", paddingLeft:"14px" },
  topicBtn:{ display:"block", width:"100%", background:"transparent", border:"none", borderLeft:"3px solid transparent", borderRadius:"0 10px 10px 0", color:"rgba(255,255,255,0.65)", padding:"10px 14px", cursor:"pointer", textAlign:"left", fontSize:"13px", fontWeight:"500", marginBottom:"2px", letterSpacing:"0.2px" },
  sidebarFooter:{ marginTop:"auto", borderTop:"1px solid rgba(255,255,255,0.1)", paddingTop:"12px" },
  main:{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden", minWidth:0 },
  header:{ background:`linear-gradient(135deg,${RED} 0%,${DARK_RED} 100%)`, color:"#fff", padding:"14px 18px", display:"flex", alignItems:"center", gap:"12px", flexShrink:0, position:"relative", overflow:"hidden" },
  headerDecor1:{ position:"absolute", top:"-30px", right:"-20px", width:"100px", height:"100px", background:"rgba(255,255,255,0.06)", borderRadius:"50%", pointerEvents:"none" },
  headerDecor2:{ position:"absolute", bottom:"-40px", left:"30%", width:"80px", height:"80px", background:"rgba(255,255,255,0.04)", borderRadius:"50%", pointerEvents:"none" },
  hamburger:{ background:"transparent", border:"none", cursor:"pointer", padding:"4px", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, borderRadius:"8px", zIndex:1 },
  headerLogoWrap:{ width:"42px", height:"42px", background:"#fff", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, boxShadow:"0 3px 12px rgba(0,0,0,0.25)", zIndex:1, overflow:"hidden" },
  headerLogo:{ width:"100%", height:"100%", objectFit:"cover" },
  headerInfo:{ flex:1, minWidth:0, zIndex:1 },
  headerTitle:{ fontWeight:"700", fontSize:"15px", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis", letterSpacing:"0.3px" },
  headerSub:{ fontSize:"11px", opacity:0.75, display:"flex", alignItems:"center", gap:"6px", marginTop:"3px" },
  dot:{ width:"7px", height:"7px", borderRadius:"50%", background:"#4ade80", display:"inline-block", flexShrink:0 },
  messages:{ flex:1, overflowY:"auto", padding:"20px 16px", display:"flex", flexDirection:"column", gap:"16px", background:"linear-gradient(180deg,#fff9fa 0%,#fff 100%)" },
  botRow:{ display:"flex", alignItems:"flex-start", gap:"10px" },
  userRow:{ display:"flex", justifyContent:"flex-end" },
  avatar:{ width:"34px", height:"34px", background:`linear-gradient(135deg,${RED},${DARK_RED})`, borderRadius:"50%", overflow:"hidden", flexShrink:0, boxShadow:`0 3px 10px rgba(192,0,42,0.4)` },
  botBubble:{ background:"#fff", borderRadius:"2px 18px 18px 18px", padding:"12px 16px", fontSize:"14px", lineHeight:"1.7", border:"1px solid rgba(192,0,42,0.1)", color:"#1a1a1a", boxShadow:"0 3px 12px rgba(0,0,0,0.06)" },
  userBubble:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, color:"#fff", borderRadius:"18px 2px 18px 18px", padding:"12px 16px", fontSize:"14px", lineHeight:"1.7", boxShadow:"0 4px 14px rgba(192,0,42,0.3)" },
  feedbackBtn:{ border:"none", borderRadius:"20px", padding:"4px 10px", fontSize:"14px", cursor:"pointer", transition:"all 0.2s" },
  chips:{ padding:"8px 14px 6px", background:"#fff", borderTop:"1px solid rgba(192,0,42,0.08)", display:"flex", gap:"6px", flexWrap:"wrap", flexShrink:0 },
  chip:{ background:"#fff5f5", border:"1.5px solid rgba(192,0,42,0.2)", borderRadius:"25px", padding:"5px 15px", fontSize:"12px", color:RED, cursor:"pointer", fontWeight:"600", letterSpacing:"0.2px" },
  inputArea:{ display:"flex", padding:"10px 14px 12px", borderTop:"1px solid rgba(192,0,42,0.08)", gap:"10px", background:"#fff", alignItems:"center", flexShrink:0 },
  input:{ flex:1, background:"#fff8f9", border:`2px solid rgba(192,0,42,0.15)`, borderRadius:"28px", padding:"10px 18px", fontSize:"14px", resize:"none", outline:"none", fontFamily:"inherit", color:"#1a1a1a", lineHeight:"1.5", boxShadow:"inset 0 2px 4px rgba(192,0,42,0.04)" },
  sendBtn:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, color:"#fff", border:"none", borderRadius:"50%", width:"46px", height:"46px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", flexShrink:0 },
  footer:{ textAlign:"center", fontSize:"11px", color:"#ccc", padding:"5px", background:"#fff", flexShrink:0, letterSpacing:"0.3px" },
};
