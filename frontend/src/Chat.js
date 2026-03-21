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

const SUGGESTED = ["How do I register for courses?","What are the BSc Computer Science fees?","When do Semester 1 exams start?","How do I apply for hostel?","What programmes does ACity offer?"];

export default function Chat() {
  const [messages, setMessages] = useState([{ role:"bot", text:"👋 Welcome! I'm the **ACity Student Assistant**.\n\nI can help you with:\n* Registration & academic calendar\n* Fees & payment methods\n* Course enrollment\n* Exams & results\n* Hostel & accommodation\n\nWhat would you like to know?" }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
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
      <div style={s.container}>

        <div style={s.header}>
          <img
            src="/logo.png"
            alt="ACity Logo"
            style={s.logoImg}
            onError={e => { e.target.style.display="none"; e.target.nextSibling.style.display="flex"; }}
          />
          <div style={s.logoFallback}>AC</div>
          <div style={s.headerInfo}>
            <div style={s.headerTitle}>ACity Student Assistant</div>
            <div style={s.headerSub}><span style={s.dot} /> Online · Academic City University College</div>
          </div>
        </div>

        <div style={s.messages}>
          {messages.map((msg, i) => (
            <div key={i} style={msg.role==="user" ? s.userRow : s.botRow}>
              {msg.role==="bot" && (
                <div style={s.avatar}><img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} /></div>
              )}
              <div style={msg.role==="user" ? s.userBubble : s.botBubble}>
                {renderText(msg.text)}
              </div>
            </div>
          ))}
          {loading && (
            <div style={s.botRow}>
              <div style={s.avatar}><img src="/logochat.png" alt="AC" style={{ width:"100%", height:"100%", objectFit:"cover" }} onError={e=>{e.target.style.display="none"}} /></div>
              <div style={{...s.botBubble, color:"#aaa", fontStyle:"italic"}}>Thinking...</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {messages.length===1 && (
          <div style={s.suggestions}>
            {SUGGESTED.map((q,i) => (
              <button key={i} style={s.chip} onClick={() => sendMessage(q)}>{q}</button>
            ))}
          </div>
        )}

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
  );
}

const s = {
  page:{ minHeight:"100vh", background:"#f1f1f1", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Segoe UI',Arial,sans-serif", padding:"16px" },
  container:{ width:"100%", maxWidth:"720px", height:"92vh", background:"#fff", borderRadius:"20px", boxShadow:"0 8px 40px rgba(0,0,0,0.12)", display:"flex", flexDirection:"column", overflow:"hidden", border:"1px solid #e5e5e5" },
  header:{ background:RED, color:"#fff", padding:"16px 20px", display:"flex", alignItems:"center", gap:"14px" },
  logoImg:{ width:"42px", height:"42px", objectFit:"contain", borderRadius:"8px", background:"#fff", padding:"4px" },
  logoFallback:{ width:"42px", height:"42px", background:"#fff", borderRadius:"10px", display:"none", alignItems:"center", justifyContent:"center", fontWeight:"900", fontSize:"16px", color:RED, flexShrink:0 },
  headerInfo:{ flex:1 },
  headerTitle:{ fontWeight:"700", fontSize:"16px" },
  headerSub:{ fontSize:"12px", opacity:0.85, display:"flex", alignItems:"center", gap:"6px", marginTop:"2px" },
  dot:{ width:"7px", height:"7px", borderRadius:"50%", background:"#4ade80", display:"inline-block" },
  messages:{ flex:1, overflowY:"auto", padding:"20px 16px", display:"flex", flexDirection:"column", gap:"16px", background:"#fafafa" },
  botRow:{ display:"flex", alignItems:"flex-start", gap:"10px" },
  userRow:{ display:"flex", justifyContent:"flex-end" },
  avatar:{ width:"34px", height:"34px", background:RED, borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"12px", fontWeight:"700", color:"#fff", flexShrink:0, overflow:"hidden" },
  botBubble:{ background:"#fff", borderRadius:"4px 16px 16px 16px", padding:"12px 16px", maxWidth:"82%", fontSize:"14px", lineHeight:"1.7", border:"1px solid #ececec", color:"#1a1a1a" },
  userBubble:{ background:RED, color:"#fff", borderRadius:"16px 4px 16px 16px", padding:"12px 16px", maxWidth:"78%", fontSize:"14px", lineHeight:"1.7" },
  suggestions:{ padding:"8px 16px 12px", display:"flex", flexWrap:"wrap", gap:"8px", background:"#fafafa", borderTop:"1px solid #ececec" },
  chip:{ background:"#fff", border:`1px solid #e0e0e0`, borderRadius:"20px", padding:"6px 14px", fontSize:"12px", color:RED, cursor:"pointer", fontWeight:"500" },
  inputArea:{ display:"flex", padding:"12px 16px", borderTop:"1px solid #ececec", gap:"10px", background:"#fff", alignItems:"flex-end" },
  input:{ flex:1, border:"1.5px solid #e0e0e0", borderRadius:"12px", padding:"10px 14px", fontSize:"14px", resize:"none", outline:"none", fontFamily:"inherit", color:"#1a1a1a", lineHeight:"1.5" },
  sendBtn:{ background:RED, color:"#fff", border:"none", borderRadius:"12px", width:"44px", height:"44px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", flexShrink:0 },
  footer:{ textAlign:"center", fontSize:"11px", color:"#aaa", padding:"6px", background:"#fff" },
};
