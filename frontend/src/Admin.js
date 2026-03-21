import { useState, useEffect } from "react";

const API = process.env.REACT_APP_API_URL;
const SECRET = "acitystudentassistant2025";

function UploadTab({ api, secret, onSave }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [proposed, setProposed] = useState([]);
  const [saving, setSaving] = useState(false);

  const extract = async () => {
    if (!file) { setStatus("Please select a file first."); return; }
    setStatus("Extracting Q&A from file...");
    setProposed([]);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${api}/admin/upload?admin_key=${secret}`, { method: "POST", headers: { "X-Admin-Key": secret }, body: formData });
      const data = await res.json();
      if (data.entries) { setProposed(data.entries); setStatus(`Found ${data.entries.length} Q&A pairs. Review and save below.`); }
      else setStatus(data.error || "Extraction failed.");
    } catch(err) { setStatus("Error: " + err.message); }
  };

  const saveAll = async () => {
    setSaving(true);
    let saved = 0;
    for (const entry of proposed) {
      await fetch(`${api}/admin/entries`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ admin_key: secret, ...entry }) });
      saved++;
    }
    setStatus(`Saved ${saved} entries to knowledge base!`);
    setProposed([]);
    setSaving(false);
    onSave();
  };

  return (
    <div>
      <h2 style={{ color:"#c0002a", marginTop:0 }}>Upload File</h2>
      <div style={{ background:"#fff", borderRadius:"12px", padding:"24px", maxWidth:"600px", boxShadow:"0 2px 8px rgba(0,0,0,0.06)" }}>
        <p style={{ color:"#64748b", fontSize:"14px", marginTop:0 }}>Upload a PDF or TXT file. Gemini will extract Q&A pairs for your review before saving.</p>
        <input type="file" accept=".pdf,.txt" onChange={e => setFile(e.target.files[0])} style={{ marginBottom:"12px", fontSize:"14px" }} />
        <br />
        <button style={{ background:"#c0002a", color:"#fff", border:"none", borderRadius:"10px", padding:"10px 24px", cursor:"pointer", fontSize:"14px" }} onClick={extract}>Extract Q&A</button>
        {status && <p style={{ color:"#64748b", fontSize:"13px", marginTop:"12px" }}>{status}</p>}
      </div>
      {proposed.length > 0 && (
        <div style={{ marginTop:"20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"12px" }}>
            <h3 style={{ color:"#1e293b", margin:0 }}>Proposed Entries ({proposed.length})</h3>
            <button style={{ background:"#c0002a", color:"#fff", border:"none", borderRadius:"10px", padding:"10px 24px", cursor:"pointer", fontSize:"14px" }} onClick={saveAll} disabled={saving}>{saving ? "Saving..." : "Save All to Knowledge Base"}</button>
          </div>
          {proposed.map((e,i) => (
            <div key={i} style={{ background:"#fff", borderRadius:"12px", padding:"16px", marginBottom:"10px", boxShadow:"0 2px 6px rgba(0,0,0,0.06)" }}>
              <span style={{ background:"#fee2e2", color:"#c0002a", fontSize:"11px", fontWeight:"700", padding:"2px 10px", borderRadius:"20px", textTransform:"uppercase" }}>{e.topic}</span>
              <div style={{ fontWeight:"600", color:"#1e293b", fontSize:"14px", marginTop:"8px" }}>{e.question}</div>
              <div style={{ color:"#64748b", fontSize:"13px", marginTop:"4px", lineHeight:"1.6" }}>{e.answer}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Admin() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("entries");
  const [entries, setEntries] = useState([]);
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ topic: "", question: "", answer: "", keywords: "" });
  const [editId, setEditId] = useState(null);
  const [msg, setMsg] = useState("");

  const login = () => {
    if (password === SECRET) { setLoggedIn(true); setError(""); }
    else setError("Wrong password. Try again.");
  };

  const headers = { "Content-Type": "application/json" };
  const body = (extra) => JSON.stringify({ admin_key: SECRET, ...extra });

  const loadEntries = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/entries?admin_key=${SECRET}`, { method: "GET", headers: { "X-Admin-Key": SECRET } });
    const d = await r.json();
    setEntries(d.entries || []);
    setLoading(false);
  };

  const loadLogs = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/logs?admin_key=${SECRET}`, { headers: { "X-Admin-Key": SECRET } });
    const d = await r.json();
    setLogs(d.logs || []);
    setLoading(false);
  };

  const loadStats = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/stats?admin_key=${SECRET}`, { headers: { "X-Admin-Key": SECRET } });
    const d = await r.json();
    setStats(d);
    setLoading(false);
  };

  useEffect(() => {
    if (!loggedIn) return;
    if (tab === "entries") loadEntries();
    if (tab === "logs") loadLogs();
    if (tab === "stats") loadStats();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loggedIn, tab]);

  const saveEntry = async () => {
    if (!form.topic || !form.question || !form.answer) { setMsg("Fill in topic, question and answer."); return; }
    const url = editId ? `${API}/admin/entries/${editId}` : `${API}/admin/entries`;
    const method = editId ? "PUT" : "POST";
    await fetch(url, { method, headers, body: body(form) });
    setMsg(editId ? "Entry updated!" : "Entry added!");
    setForm({ topic: "", question: "", answer: "", keywords: "" });
    setEditId(null);
    loadEntries();
  };

  const deleteEntry = async (id) => {
    if (!window.confirm("Deactivate this entry?")) return;
    await fetch(`${API}/admin/entries/${id}`, { method: "DELETE", headers, body: body({}) });
    setMsg("Entry deactivated.");
    loadEntries();
  };

  const startEdit = (e) => {
    setEditId(e.id);
    setForm({ topic: e.topic, question: e.question, answer: e.answer, keywords: e.keywords || "" });
    setTab("add");
  };

  if (!loggedIn) return (
    <div style={s.page}>
      <div style={s.loginBox}>
        <div style={s.logoBox}><img src="/admin.png" alt="Admin" style={{ width:"100%", height:"100%", objectFit:"contain", borderRadius:"8px" }} onError={e=>{e.target.style.display="none"}} /></div>
        <h2 style={s.loginTitle}>ACity Admin Panel</h2>
        <p style={s.loginSub}>Enter your admin password to continue</p>
        <input style={s.input} type="password" placeholder="Admin password"
          value={password} onChange={e => setPassword(e.target.value)}
          onKeyDown={e => e.key === "Enter" && login()} />
        {error && <div style={s.error}>{error}</div>}
        <button style={s.btn} onClick={login}>Login</button>
      </div>
    </div>
  );

  return (
    <div style={s.page}>
      <div style={s.shell}>
        <div style={s.sidebar}>
          <div style={s.sideHeader}>
            <div style={s.logoBox}><img src="/admin.png" alt="Admin" style={{ width:"100%", height:"100%", objectFit:"contain", borderRadius:"8px" }} onError={e=>{e.target.style.display="none"}} /></div>
            <div>
              <div style={s.sideTitle}>Admin Panel</div>
              <div style={s.sideSub}>ACity Student Assistant</div>
            </div>
          </div>
          {["entries","add","logs","stats","upload"].map(t => (
            <button key={t} style={{...s.navBtn, ...(tab===t?s.navActive:{})}} onClick={() => { setTab(t); setMsg(""); setEditId(null); setForm({ topic:"",question:"",answer:"",keywords:"" }); }}>
              {t === "entries" && "📋 Knowledge Base"}
              {t === "add" && "➕ Add Entry"}
              {t === "logs" && "💬 Chat Logs"}
              {t === "stats" && "📊 Analytics"}{t === "upload" && "📎 Upload File"}
              {t === "upload" && "📎 Upload File"}
            </button>
          ))}
          <button style={s.logoutBtn} onClick={() => setLoggedIn(false)}>🚪 Logout</button>
        </div>

        <div style={s.main}>
          {msg && <div style={s.success}>{msg}</div>}

          {tab === "entries" && (
            <div>
              <h2 style={s.heading}>Knowledge Base ({entries.filter(e=>e.active).length} active)</h2>
              {loading ? <p>Loading...</p> : entries.filter(e=>e.active).map(e => (
                <div key={e.id} style={s.card}>
                  <div style={s.cardTopic}>{e.topic}</div>
                  <div style={s.cardQ}>{e.question}</div>
                  <div style={s.cardA}>{e.answer}</div>
                  <div style={s.cardActions}>
                    <button style={s.editBtn} onClick={() => startEdit(e)}>Edit</button>
                    <button style={s.deleteBtn} onClick={() => deleteEntry(e.id)}>Deactivate</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "add" && (
            <div>
              <h2 style={s.heading}>{editId ? "Edit Entry" : "Add New Entry"}</h2>
              <div style={s.form}>
                <select style={s.input} value={form.topic} onChange={e=>setForm({...form,topic:e.target.value})}>
                  <option value="">Select topic</option>
                  {["fees","registration","exams","hostel","enrollment","general"].map(t=>(
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <input style={s.input} placeholder="Question" value={form.question} onChange={e=>setForm({...form,question:e.target.value})} />
                <textarea style={{...s.input,height:"120px",resize:"vertical"}} placeholder="Answer" value={form.answer} onChange={e=>setForm({...form,answer:e.target.value})} />
                <input style={s.input} placeholder="Keywords (optional)" value={form.keywords} onChange={e=>setForm({...form,keywords:e.target.value})} />
                <button style={s.btn} onClick={saveEntry}>{editId ? "Update Entry" : "Add Entry"}</button>
                {editId && <button style={{...s.btn,background:"#64748b",marginLeft:"10px"}} onClick={()=>{setEditId(null);setForm({topic:"",question:"",answer:"",keywords:""})}}>Cancel</button>}
              </div>
            </div>
          )}

          {tab === "logs" && (
            <div>
              <h2 style={s.heading}>Recent Conversations ({logs.length})</h2>
              {loading ? <p>Loading...</p> : logs.map((l,i) => (
                <div key={i} style={s.card}>
                  <div style={s.cardTopic}>{l.topic}</div>
                  <div style={s.cardQ}>Q: {l.question}</div>
                  <div style={s.cardA}>A: {l.answer?.slice(0,200)}{l.answer?.length>200?"...":""}</div>
                </div>
              ))}
            </div>
          )}

          {tab === "upload" && <UploadTab api={API} secret={SECRET} onSave={loadEntries} />}

          {tab === "stats" && (
            <div>
              <h2 style={s.heading}>Analytics</h2>
              {loading ? <p>Loading...</p> : (
                <div>
                  <div style={s.statBox}><div style={s.statNum}>{stats.total_questions || 0}</div><div style={s.statLabel}>Total Questions Asked</div></div>
                  <h3 style={{color:"#1e293b",marginTop:"24px"}}>Questions by Topic</h3>
                  {Object.entries(stats.by_topic || {}).map(([topic, count]) => (
                    <div key={topic} style={s.statRow}>
                      <div style={s.statTopic}>{topic}</div>
                      <div style={s.statBar}><div style={{...s.statFill,width:`${Math.min((count/(stats.total_questions||1))*100,100)}%`}} /></div>
                      <div style={s.statCount}>{count}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const s = {
  page: { minHeight:"100vh", background:"linear-gradient(135deg,#c0002a,#8b0020)", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Segoe UI',Arial,sans-serif", padding:"16px" },
  loginBox: { background:"#fff", borderRadius:"20px", padding:"40px", width:"100%", maxWidth:"400px", textAlign:"center", boxShadow:"0 20px 60px rgba(0,0,0,0.3)" },
  logoBox: { width:"56px", height:"56px", background:"#f5a623", borderRadius:"14px", display:"flex", alignItems:"center", justifyContent:"center", margin:"0 auto 16px" },
  logoText: { fontWeight:"900", fontSize:"28px", color:"#c0002a" },
  loginTitle: { color:"#c0002a", margin:"0 0 8px", fontSize:"22px" },
  loginSub: { color:"#64748b", margin:"0 0 24px", fontSize:"14px" },
  input: { width:"100%", border:"2px solid #e2e8f0", borderRadius:"10px", padding:"12px 14px", fontSize:"14px", marginBottom:"12px", boxSizing:"border-box", fontFamily:"inherit" },
  error: { color:"#ef4444", marginBottom:"12px", fontSize:"14px" },
  success: { background:"#d1fae5", color:"#065f46", padding:"12px 16px", borderRadius:"10px", marginBottom:"16px", fontSize:"14px" },
  btn: { background:"#c0002a", color:"#fff", border:"none", borderRadius:"10px", padding:"12px 24px", fontSize:"15px", cursor:"pointer", width:"100%" },
  shell: { width:"100%", maxWidth:"1100px", height:"92vh", display:"flex", borderRadius:"20px", overflow:"hidden", boxShadow:"0 20px 60px rgba(0,0,0,0.3)" },
  sidebar: { width:"220px", background:"#c0002a", display:"flex", flexDirection:"column", padding:"24px 16px", gap:"4px", flexShrink:0 },
  sideHeader: { display:"flex", alignItems:"center", gap:"12px", marginBottom:"24px" },
  sideTitle: { color:"#fff", fontWeight:"700", fontSize:"14px" },
  sideSub: { color:"#93c5fd", fontSize:"11px" },
  navBtn: { background:"transparent", border:"none", color:"#93c5fd", padding:"10px 12px", borderRadius:"8px", cursor:"pointer", textAlign:"left", fontSize:"13px", fontWeight:"500" },
  navActive: { background:"rgba(255,255,255,0.15)", color:"#fff" },
  logoutBtn: { background:"transparent", border:"none", color:"#f87171", padding:"10px 12px", borderRadius:"8px", cursor:"pointer", textAlign:"left", fontSize:"13px", marginTop:"auto" },
  main: { flex:1, background:"#f8fafc", padding:"24px", overflowY:"auto" },
  heading: { color:"#c0002a", marginTop:0, fontSize:"20px" },
  card: { background:"#fff", borderRadius:"12px", padding:"16px", marginBottom:"12px", boxShadow:"0 2px 8px rgba(0,0,0,0.06)" },
  cardTopic: { display:"inline-block", background:"#dbeafe", color:"#1d4ed8", fontSize:"11px", fontWeight:"700", padding:"2px 10px", borderRadius:"20px", marginBottom:"8px", textTransform:"uppercase" },
  cardQ: { fontWeight:"600", color:"#1e293b", fontSize:"14px", marginBottom:"6px" },
  cardA: { color:"#64748b", fontSize:"13px", lineHeight:"1.6" },
  cardActions: { marginTop:"12px", display:"flex", gap:"8px" },
  editBtn: { background:"#c0002a", color:"#fff", border:"none", borderRadius:"6px", padding:"6px 14px", cursor:"pointer", fontSize:"12px" },
  deleteBtn: { background:"#fee2e2", color:"#ef4444", border:"none", borderRadius:"6px", padding:"6px 14px", cursor:"pointer", fontSize:"12px" },
  form: { background:"#fff", borderRadius:"12px", padding:"24px", maxWidth:"600px", boxShadow:"0 2px 8px rgba(0,0,0,0.06)" },
  statBox: { background:"#c0002a", color:"#fff", borderRadius:"16px", padding:"24px", textAlign:"center", marginBottom:"16px" },
  statNum: { fontSize:"48px", fontWeight:"900" },
  statLabel: { fontSize:"14px", opacity:0.8 },
  statRow: { display:"flex", alignItems:"center", gap:"12px", marginBottom:"12px" },
  statTopic: { width:"100px", fontSize:"13px", color:"#1e293b", fontWeight:"600", textTransform:"capitalize" },
  statBar: { flex:1, background:"#e2e8f0", borderRadius:"20px", height:"10px", overflow:"hidden" },
  statFill: { height:"100%", background:"#c0002a", borderRadius:"20px", transition:"width 0.5s" },
  statCount: { width:"30px", fontSize:"13px", color:"#64748b", textAlign:"right" },
};
