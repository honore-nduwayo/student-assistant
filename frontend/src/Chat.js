import { useState, useRef, useEffect } from "react";

const RED = "#c0002a";

function renderInlineLinks(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const parts = text.split(urlRegex);
  return parts.map((part, i) => {
    if (part.match(/^https?:\/\//)) {
      return (<a key={i} href={part} target="_blank" rel="noreferrer" style={{ color: RED, textDecoration: "underline", wordBreak: "break-all" }}>{part}</a>);
    }
    const boldParts = part.split(/\*\*(.*?)\*\*/g);
    return boldParts.map((bp, j) => j % 2 === 1 ? <strong key={`${i}-${j}`}>{bp}</strong> : bp);
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
  { label: "Fees & Payments", q: "What are the tuition fees at ACity?" },
  { label: "Registration", q: "How do I register for courses?" },
  { label: "Exams", q: "When do Semester 1 exams start?" },
  { label: "Hostel", q: "How do I apply for hostel?" },
  { label: "Enrollment", q: "How do I enroll in courses?" },
  { label: "Programmes", q: "What programmes does ACity offer?" },
  { label: "Scholarships", q: "What scholarships are available at ACity?" },
  { label: "Contact", q: "What are the contact details for ACity?" },
];

export default function Chat() {
  const [messages, setMessages] = useState([{ role:"bot", text:"👋 Welcome! I'm the **ACity Student Assistant**.\n\nI can help you with:\n* Registration & academic calendar\n* Fees & payment methods\n* Course enrollment\n* Exams & results\n* Hostel & accommodation\n\nWhat would you like to know?" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  const sendMessage = async (text) => {
    const question = (text || input).trim();
    if (!question) return;
    setInput("");
    const newMessages = [...messages, { role:"user", text:question }];
    setMessages(newMessages);
    setLoading(true);
    try {
      const res = await fetch(`${process.env.REACT_APP_API_URL}/ask`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ question, history:newMessages.slice(-10) }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role:"bot", text:data.answer }]);
    } catch {
      setMessages(prev => [...prev, { role:"bot", text:"Sorry, I could not connect to the server. Please try again.\n\nFor urgent queries contact: registry@acity.edu.gh" }]);
    }
    setLoading(false);
  };

  return (
    <div style={s.page}>
      <style>{`
        @media (max-width: 600px) {
          .sidebar { min-width: 160px !important; width: 160px !important; }
          .chat-shell { border-radius: 0 !important; height: 100vh !important; height: 100dvh !important; }
          .page-wrap { padding: 0 !important; background: #fff !important; }
        }
      `}</style>

      <div className="page-wrap" style={s.pageWrap}>
        <div className="chat-shell" style={s.shell}>

          {/* Sidebar */}
          <div className="sidebar" style={{ ...s.sidebar, width: sidebarOpen ? "200px" : "0px", minWidth: sidebarOpen ? "200px" : "0px", overflow:"hidden", transition:"all 0.3s ease" }}>
            <div style={{ padding:"20px 14px", display:"flex", flexDirection:"column", gap:"10px", minWidth:"200px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"8px" }}>
                <img src="/logo.png" alt="ACity" style={{ width:"36px", height:"36px", objectFit:"contain", background:"#fff", borderRadius:"8px", padding:"3px" }} onError={e=>{e.target.style.display="none"}} />
                <div style={{ color:"#fff" }}>
                  <div style={{ fontWeight:"700", fontSize:"13px" }}>ACity</div>
                  <div style={{ fontSize:"11px", opacity:0.7 }}>Student Assistant</div>
                </div>
              </div>
              <div style={{ borderTop:"1px solid rgba(255,255,255,0.2)", paddingTop:"12px" }}>
                <div style={{ color:"rgba(255,255,255,0.5)", fontSize:"10px", fontWeight:"700", textTransform:"uppercase", letterSpacing:"0.5px", marginBottom:"8px" }}>Quick Topics</div>
                {TOPICS.map((t, i) => (
                  <button key={i} onClick={() => sendMessage(t.q)} style={s.topicBtn}>{t.label}</button>
                ))}
              </div>
              <div style={{ marginTop:"auto", borderTop:"1px solid rgba(255,255,255,0.2)", paddingTop:"12px" }}>
                <div style={{ color:"rgba(255,255,255,0.5)", fontSize:"10px" }}>Powered by AI</div>
                <div style={{ color:"rgba(255,255,255,0.5)", fontSize:"10px" }}>Official ACity info only</div>
              </div>
            </div>
          </div>

          {/* Main chat area */}
          <div style={s.main}>
            <div style={s.header}>
              <button onClick={() => setSidebarOpen(!sidebarOpen)} style={s.toggleBtn} title="Toggle sidebar">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                  <line x1="3" y1="6" x2="21" y2="6"/>
                  <line x1="3" y1="12" x2="21" y2="12"/>
                  <line x1="3" y1="18" x2="21" y2="18"/>
                </svg>
              </button>
              <img src="/logo.png" alt="ACity" style={s.logoImg} onError={e=>{e.target.style.display="none"}} />
              <div style={s.headerInfo}>
                <div style={s.headerTitle}>ACity Student Assistant</div>
                <div style={s.headerSub}><span style={s.dot} /> Online · Academic City University College</div>
              </div>
            </div>

            <div style={s.messages}>
              {messages.map((msg, i) => (
                <div key={i} style={msg.role==="user" ? s.userRow : s.botRow}>
                  {msg.role==="bot" && (
                    <div style={s.avatar}>
                      <img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} />
                    </div>
                  )}
                  <div style={msg.role==="user" ? s.userBubble : s.botBubble}>
                    {renderText(msg.text)}
                  </div>
                </div>
              ))}
              {loading && (
                <div style={s.botRow}>
                  <div style={s.avatar}>
                    <img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} />
                  </div>
                  <div style={{...s.botBubble, color:"#aaa", fontStyle:"italic"}}>Thinking...</div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <div style={s.inputArea}>
              <textarea
                style={s.input}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); sendMessage(); }}}
                placeholder="Type your question and press Enter..."
                rows={2}
              />
              <button style={s.sendBtn} onClick={() => sendMessage()} disabled={loading}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
            <div style={s.footer}>Powered by AI · Official ACity information only</div>
          </div>

        </div>
      </div>
    </div>
  );
}

const s = {
  page:{ minHeight:"100vh", background:"#c0002a", display:"flex", fontFamily:"'Segoe UI',Arial,sans-serif", margin:"0", padding:"0" },
  pageWrap:{ width:"100%", padding:"0", margin:"0" },
  shell:{ display:"flex", width:"100vw", height:"100vh", background:"#fff", overflow:"hidden" },
  sidebar:{ background:RED, display:"flex", flexDirection:"column" },
  topicBtn:{ display:"block", width:"100%", background:"transparent", border:"none", color:"rgba(255,255,255,0.8)", padding:"8px 10px", borderRadius:"8px", cursor:"pointer", textAlign:"left", fontSize:"12px", fontWeight:"500", marginBottom:"2px", transition:"background 0.2s" },
  main:{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" },
  header:{ background:RED, color:"#fff", padding:"14px 18px", display:"flex", alignItems:"center", gap:"12px" },
  toggleBtn:{ background:"transparent", border:"none", cursor:"pointer", padding:"4px", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0, borderRadius:"6px" },
  logoImg:{ width:"38px", height:"38px", objectFit:"contain", borderRadius:"8px", background:"#fff", padding:"3px", flexShrink:0 },
  headerInfo:{ flex:1 },
  headerTitle:{ fontWeight:"700", fontSize:"15px" },
  headerSub:{ fontSize:"11px", opacity:0.85, display:"flex", alignItems:"center", gap:"5px", marginTop:"2px" },
  dot:{ width:"7px", height:"7px", borderRadius:"50%", background:"#4ade80", display:"inline-block" },
  messages:{ flex:1, overflowY:"auto", padding:"20px 16px", display:"flex", flexDirection:"column", gap:"16px", background:"#fafafa" },
  botRow:{ display:"flex", alignItems:"flex-start", gap:"10px" },
  userRow:{ display:"flex", justifyContent:"flex-end" },
  avatar:{ width:"34px", height:"34px", background:RED, borderRadius:"50%", overflow:"hidden", flexShrink:0 },
  botBubble:{ background:"#fff", borderRadius:"4px 16px 16px 16px", padding:"12px 16px", maxWidth:"82%", fontSize:"14px", lineHeight:"1.7", border:"1px solid #ececec", color:"#1a1a1a" },
  userBubble:{ background:RED, color:"#fff", borderRadius:"16px 4px 16px 16px", padding:"12px 16px", maxWidth:"78%", fontSize:"14px", lineHeight:"1.7" },
  inputArea:{ display:"flex", padding:"12px 16px", borderTop:"1px solid #ececec", gap:"10px", background:"#fff", alignItems:"flex-end" },
  input:{ flex:1, border:"1.5px solid #e0e0e0", borderRadius:"12px", padding:"10px 14px", fontSize:"14px", resize:"none", outline:"none", fontFamily:"inherit", color:"#1a1a1a", lineHeight:"1.5" },
  sendBtn:{ background:RED, color:"#fff", border:"none", borderRadius:"12px", width:"44px", height:"44px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", flexShrink:0 },
  footer:{ textAlign:"center", fontSize:"11px", color:"#aaa", padding:"6px", background:"#fff" },
};
