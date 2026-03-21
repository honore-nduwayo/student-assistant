import { useState, useEffect } from "react";

const RED = "#c0002a";
const DARK_RED = "#6b0015";
const API = process.env.REACT_APP_API_URL;


const css = `
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  @keyframes activeGlow { 0%,100%{box-shadow:inset 0 0 0 0 rgba(255,255,255,0)} 50%{box-shadow:inset 4px 0 12px rgba(255,255,255,0.1)} }
  @keyframes sendGlow { 0%,100%{box-shadow:0 4px 15px rgba(192,0,42,0.35)} 50%{box-shadow:0 4px 25px rgba(192,0,42,0.6)} }

  .nav-item {
    transition: all 0.3s cubic-bezier(0.4,0,0.2,1);
    position: relative;
    overflow: hidden;
    border-left: 4px solid transparent !important;
  }
  .nav-item::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 0;
    background: rgba(255,255,255,0.08);
    transition: width 0.3s ease;
  }
  .nav-item:hover::before { width: 100%; }
  .nav-item:hover { border-left-color: rgba(255,255,255,0.5) !important; transform: translateX(3px); }
  .nav-item.active { background: rgba(255,255,255,0.2) !important; border-left-color: #fff !important; animation: activeGlow 3s infinite; }
  .nav-item.active .nav-ml { color: #fff !important; font-weight: 800 !important; }
  .nav-item.active .nav-sl { color: rgba(255,255,255,0.6) !important; }
  .nav-item:hover .nav-ml { color: #fff !important; }
  .nav-item.active .nav-dot { background: #fff !important; box-shadow: 0 0 8px rgba(255,255,255,0.8); }
  .nav-item:hover .nav-dot { background: rgba(255,255,255,0.7) !important; }
  .nav-badge { opacity: 0; transform: translateX(4px); transition: all 0.25s ease; }
  .nav-item.active .nav-badge { opacity: 1 !important; transform: translateX(0) !important; }
  .nav-item:hover .nav-badge { opacity: 1 !important; transform: translateX(0) !important; }

  .entry-card { transition: all 0.25s cubic-bezier(0.4,0,0.2,1); }
  .entry-card:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(0,0,0,0.1) !important; }
  .pill-btn { transition: all 0.2s ease; }
  .pill-btn:hover { transform: translateY(-1px); filter: brightness(1.1); }
  .pill-outline:hover { background: #fff0f0 !important; }
  .anim { animation: fadeUp 0.35s ease both; }
  .glow-btn { animation: sendGlow 2.5s infinite; }
  .signout-btn { transition: all 0.2s ease; }
  .signout-btn:hover { background: rgba(255,255,255,0.1) !important; color: rgba(255,255,255,0.7) !important; }
`;

const TOPIC_COLORS = {
  fees: { bg:"linear-gradient(135deg,#fee2e2,#fecaca)", color:"#b91c1c" },
  registration: { bg:"linear-gradient(135deg,#dbeafe,#bfdbfe)", color:"#1d4ed8" },
  exams: { bg:"linear-gradient(135deg,#fef3c7,#fde68a)", color:"#b45309" },
  hostel: { bg:"linear-gradient(135deg,#d1fae5,#a7f3d0)", color:"#065f46" },
  enrollment: { bg:"linear-gradient(135deg,#e0e7ff,#c7d2fe)", color:"#4338ca" },
  general: { bg:"linear-gradient(135deg,#ede9fe,#ddd6fe)", color:"#6d28d9" },
};

const TABS = [
  { key:"entries", label:"Knowledge Base", sub:"Manage Q&A entries" },
  { key:"add", label:"Add Entry", sub:"Create new Q&A pair" },
  { key:"logs", label:"Chat Logs", sub:"Recent conversations" },
  { key:"stats", label:"Analytics", sub:"Usage & satisfaction" },
  { key:"upload", label:"Upload File", sub:"PDF, TXT, DOCX" },
  { key:"settings", label:"Settings", sub:"Password & config" },
];

function SettingsTab({ secret }) {
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [confirm, setConfirm] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setMsg(""); setErr("");
    if (newPass.length < 6) { setErr("New password must be at least 6 characters."); return; }
    if (newPass !== confirm) { setErr("Passwords do not match."); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API}/admin/password`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ admin_key: current, new_password: newPass })
      });
      const data = await res.json();
      if (data.success) {
        setMsg("Password updated! All devices will use the new password immediately.");
        setCurrent(""); setNewPass(""); setConfirm("");
      } else {
        setErr(data.error || "Failed to update password.");
      }
    } catch(e) { setErr("Connection error. Try again."); }
    setSaving(false);
  };

  return (
    <div className="anim">
      <div style={dash.sectionHeader}>
        <div><div style={dash.sectionTitle}>Settings</div><div style={dash.sectionSub}>Change your admin password</div></div>
      </div>
      <div style={dash.card}>
        <p style={{ color:"#777", fontSize:"14px", marginTop:0, lineHeight:"1.7" }}>Password is stored securely and syncs across all devices instantly.</p>
        <p style={{ color:"#aaa", fontSize:"12px", marginTop:0, lineHeight:"1.7" }}>💡 If you forget your password, use the master key: <strong>acitystudentassistant2025</strong></p>
        <input style={dash.input} type="password" placeholder="Current password (or master key)" value={current} onChange={e=>setCurrent(e.target.value)} />
        <input style={dash.input} type="password" placeholder="New password (min 6 characters)" value={newPass} onChange={e=>setNewPass(e.target.value)} />
        <input style={dash.input} type="password" placeholder="Confirm new password" value={confirm} onChange={e=>setConfirm(e.target.value)} />
        {err && <div style={{ color:"#ef4444", fontSize:"13px", marginBottom:"12px" }}>{err}</div>}
        {msg && <div style={{ color:"#065f46", fontSize:"13px", marginBottom:"12px", background:"#d1fae5", padding:"10px 14px", borderRadius:"10px" }}>{msg}</div>}
        <button className="pill-btn glow-btn" onClick={save} disabled={saving} style={dash.primaryBtn}>{saving ? "Saving..." : "Update Password"}</button>
      </div>
    </div>
  );
}

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
      const res = await fetch(`${api}/admin/upload?admin_key=${secret}`, { method:"POST", headers:{"X-Admin-Key":secret}, body:formData });
      const data = await res.json();
      if (data.entries) { setProposed(data.entries); setStatus(`Found ${data.entries.length} Q&A pairs. Review and save below.`); }
      else setStatus(data.error || "Extraction failed.");
    } catch(err) { setStatus("Error: " + err.message); }
  };

  const saveAll = async () => {
    setSaving(true);
    for (const entry of proposed) {
      await fetch(`${api}/admin/entries`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ admin_key:secret, ...entry }) });
    }
    setStatus(`Saved ${proposed.length} entries!`);
    setProposed([]);
    setSaving(false);
    onSave();
  };

  return (
    <div className="anim">
      <div style={dash.sectionHeader}>
        <div><div style={dash.sectionTitle}>Upload File</div><div style={dash.sectionSub}>PDF, TXT, or DOCX — AI extracts Q&A automatically</div></div>
      </div>
      <div style={dash.card}>
        <p style={{ color:"#777", fontSize:"14px", marginTop:0, lineHeight:"1.7" }}>Upload an official ACity document. Gemini will generate Q&A pairs for your review before saving.</p>
        <input type="file" accept=".pdf,.txt,.docx" onChange={e=>setFile(e.target.files[0])} style={{ marginBottom:"14px", fontSize:"14px", color:"#555" }} />
        <br />
        <button className="pill-btn glow-btn" onClick={extract} style={dash.primaryBtn}>Extract Q&A</button>
        {status && <p style={{ color:"#777", fontSize:"13px", marginTop:"12px" }}>{status}</p>}
      </div>
      {proposed.length > 0 && (
        <div style={{ marginTop:"20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"14px" }}>
            <div style={dash.sectionTitle}>Proposed ({proposed.length})</div>
            <button className="pill-btn glow-btn" onClick={saveAll} disabled={saving} style={dash.primaryBtn}>{saving?"Saving...":"Save All"}</button>
          </div>
          {proposed.map((e,i) => {
            const tc = TOPIC_COLORS[e.topic] || TOPIC_COLORS.general;
            return (
              <div key={i} className="entry-card" style={dash.card}>
                <span style={{ background:tc.bg, color:tc.color, fontSize:"9px", fontWeight:"800", padding:"3px 12px", borderRadius:"25px", textTransform:"uppercase", letterSpacing:"0.8px" }}>{e.topic}</span>
                <div style={{ fontWeight:"600", color:"#111", fontSize:"14px", marginTop:"10px" }}>{e.question}</div>
                <div style={{ color:"#777", fontSize:"13px", marginTop:"4px", lineHeight:"1.6" }}>{e.answer}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Sidebar({ tab, setTab, setMsg, setEditId, setForm, sidebarOpen, setSidebarOpen, setLoggedIn, isMobile, entries }) {
  

  return (
    <div style={{
      ...s.sidebar,
      width: sidebarOpen ? "240px" : "70px",
      minWidth: sidebarOpen ? "240px" : "70px",
      position: isMobile ? "fixed" : "relative",
      transform: isMobile ? (sidebarOpen ? "translateX(0)" : "translateX(-100%)") : "translateX(0)",
      zIndex: isMobile ? 300 : 1,
      height: isMobile ? "100dvh" : "100%",
      transition: "all 0.35s cubic-bezier(0.4,0,0.2,1)",
    }}>
      {/* Header */}
      <div style={s.sidebarHeader}>
        {sidebarOpen && (
          <div style={{ display:"flex", alignItems:"center", gap:"10px", flex:1, overflow:"hidden" }}>
            <div style={s.sidebarLogoWrap}>
              <img src="/admin.png" alt="Admin" style={{ width:"100%", height:"100%", objectFit:"contain" }} onError={e=>{e.target.style.display="none"}} />
            </div>
            <div>
              <div style={{ color:"#fff", fontSize:"15px", fontWeight:"800", letterSpacing:"0.4px", whiteSpace:"nowrap" }}>Admin</div>
              <div style={{ color:"rgba(255,255,255,0.4)", fontSize:"10px", letterSpacing:"1px", textTransform:"uppercase" }}>Dashboard</div>
            </div>
          </div>
        )}
        <button onClick={() => setSidebarOpen(!sidebarOpen)} style={s.toggleBtn}>
          <div style={{ display:"flex", flexDirection:"column", gap:"3.5px" }}>
            <div style={{ width:"14px", height:"1.5px", background:"rgba(255,255,255,0.8)", borderRadius:"2px" }}></div>
            <div style={{ width:"14px", height:"1.5px", background:"rgba(255,255,255,0.8)", borderRadius:"2px" }}></div>
            <div style={{ width:"14px", height:"1.5px", background:"rgba(255,255,255,0.8)", borderRadius:"2px" }}></div>
          </div>
        </button>
      </div>

      {sidebarOpen && (
        <div style={{ color:"rgba(255,255,255,0.3)", fontSize:"9px", fontWeight:"800", letterSpacing:"2px", textTransform:"uppercase", padding:"0 16px", marginBottom:"8px" }}>Navigation</div>
      )}

      {/* Nav items */}
      <div style={{ flex:1 }}>
        {TABS.map(t => (
          <button
            key={t.key}
            className={`nav-item${tab===t.key?" active":""}`}
            onClick={() => { setTab(t.key); setMsg(""); setEditId(null); setForm({ topic:"",question:"",answer:"",keywords:"" }); if(isMobile) setSidebarOpen(false); }}
            style={{
              ...s.navBtn,
              justifyContent: sidebarOpen ? "space-between" : "center",
              padding: sidebarOpen ? "14px 14px 14px 16px" : "14px 0",
            }}
          >
            {sidebarOpen ? (
              <>
                <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
                  <div className="nav-dot" style={{ width:"8px", height:"8px", borderRadius:"50%", background: tab===t.key ? "#fff" : "rgba(255,255,255,0.25)", flexShrink:0, transition:"all 0.3s", boxShadow: tab===t.key ? "0 0 8px rgba(255,255,255,0.8)" : "none" }}></div>
                  <div>
                    <div className="nav-ml" style={{ color: tab===t.key ? "#fff" : "rgba(255,255,255,0.65)", fontSize:"14px", fontWeight: tab===t.key ? "800" : "600", letterSpacing:"0.3px" }}>{t.label}</div>
                    <div className="nav-sl" style={{ color: tab===t.key ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.3)", fontSize:"10px", marginTop:"2px" }}>{t.sub}</div>
                  </div>
                </div>
                {t.key==="entries" && (
                  <div className="nav-badge" style={{ background:"rgba(255,255,255,0.25)", color:"#fff", fontSize:"10px", fontWeight:"800", padding:"2px 9px", borderRadius:"20px", opacity: tab===t.key ? 1 : 0, transform: tab===t.key ? "translateX(0)" : "translateX(4px)" }}>{entries.filter(e=>e.active).length || ""}</div>
                )}
              </>
            ) : (
              <div style={{ width:"8px", height:"8px", borderRadius:"50%", background: tab===t.key ? "#fff" : "rgba(255,255,255,0.25)", boxShadow: tab===t.key ? "0 0 8px rgba(255,255,255,0.8)" : "none" }}></div>
            )}
          </button>
        ))}
      </div>

      {/* Sign out */}
      <button className="signout-btn" onClick={() => setLoggedIn(false)} style={{ ...s.signOutBtn, padding: sidebarOpen ? "11px 16px" : "11px 0", justifyContent: sidebarOpen ? "flex-start" : "center" }}>
        {sidebarOpen ? "Sign Out" : "—"}
      </button>
    </div>
  );
}

export default function Admin() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [adminSecret, setAdminSecret] = useState("");
  useEffect(() => { // eslint-disable-line react-hooks/exhaustive-deps
    fetch(`${API}/admin/password`)
      .then(r=>r.json())
      .then(d=>setAdminSecret(d.password||"acitystudentassistant2025"))
      .catch(()=>setAdminSecret("acitystudentassistant2025"));
  }, []);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState("entries");
  const [entries, setEntries] = useState([]);
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ topic:"", question:"", answer:"", keywords:"" });
  const [editId, setEditId] = useState(null);
  const [msg, setMsg] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const isMobile = window.innerWidth <= 768;

  const login = () => {
    if (password === adminSecret) { setLoggedIn(true); setError(""); }
    else setError("Incorrect password. Try again.");
  };

  const headers = { "Content-Type":"application/json" };
  const body = (extra) => JSON.stringify({ admin_key:adminSecret, ...extra });

  const loadEntries = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/entries?admin_key=${adminSecret}`, { headers:{"X-Admin-Key":adminSecret} });
    const d = await r.json();
    setEntries(d.entries || []);
    setLoading(false);
  };

  const loadLogs = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/logs?admin_key=${adminSecret}`, { headers:{"X-Admin-Key":adminSecret} });
    const d = await r.json();
    setLogs(d.logs || []);
    setLoading(false);
  };

  const loadStats = async () => {
    setLoading(true);
    const r = await fetch(`${API}/admin/stats?admin_key=${adminSecret}`, { headers:{"X-Admin-Key":adminSecret} });
    const d = await r.json();
    setStats(d);
    setLoading(false);
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!loggedIn) return;
    if (tab === "entries") loadEntries();
    if (tab === "logs") loadLogs();
    if (tab === "stats") loadStats();
  }, [loggedIn, tab]); // eslint-disable-line react-hooks/exhaustive-deps // eslint-disable-line react-hooks/exhaustive-deps

  const saveEntry = async () => {
    if (!form.topic || !form.question || !form.answer) { setMsg("Fill in topic, question and answer."); return; }
    const url = editId ? `${API}/admin/entries/${editId}` : `${API}/admin/entries`;
    const method = editId ? "PUT" : "POST";
    await fetch(url, { method, headers, body:body(form) });
    setMsg(editId ? "Entry updated!" : "Entry added!");
    setForm({ topic:"", question:"", answer:"", keywords:"" });
    setEditId(null);
    loadEntries();
  };

  const deleteEntry = async (id) => {
    if (!window.confirm("Deactivate this entry?")) return;
    await fetch(`${API}/admin/entries/${id}`, { method:"DELETE", headers, body:body({}) });
    setMsg("Entry deactivated.");
    loadEntries();
  };

  const startEdit = (e) => {
    setEditId(e.id);
    setForm({ topic:e.topic, question:e.question, answer:e.answer, keywords:e.keywords||"" });
    setTab("add");
  };

  if (!loggedIn) return (
    <div style={s.loginPage}>
      <style>{css}</style>
      <div style={s.loginDecor1} /><div style={s.loginDecor2} />
      <div style={s.loginBox}>
        <div style={s.loginLogoWrap}>
          <img src="/admin.png" alt="Admin" style={{ width:"100%", height:"100%", objectFit:"contain" }} onError={e=>{e.target.style.display="none"}} />
        </div>
        <div style={s.loginTitle}>Admin Panel</div>
        <div style={s.loginSub}>ACity Student Assistant</div>
        <input style={s.loginInput} type="password" placeholder="Enter admin password" value={password} onChange={e=>setPassword(e.target.value)} onKeyDown={e=>e.key==="Enter"&&login()} />
        {error && <div style={s.loginError}>{error}</div>}
        <button className="pill-btn glow-btn" onClick={login} style={s.loginBtn}>Sign In</button>
      </div>
    </div>
  );

  return (
    <div style={s.page}>
      <style>{css}</style>
      {isMobile && sidebarOpen && <div onClick={()=>setSidebarOpen(false)} style={s.overlay} />}
      <Sidebar tab={tab} setTab={setTab} setMsg={setMsg} setEditId={setEditId} setForm={setForm} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} setLoggedIn={setLoggedIn} isMobile={isMobile} entries={entries} />
      <div style={s.main}>
        {/* Top bar */}
        <div style={s.topBar}>
          {isMobile && (
            <button onClick={()=>setSidebarOpen(true)} style={s.mobileMenuBtn}>
              <div style={{ display:"flex", flexDirection:"column", gap:"3px" }}>
                <div style={{ width:"16px", height:"1.5px", background:"#fff", borderRadius:"2px" }}></div>
                <div style={{ width:"16px", height:"1.5px", background:"#fff", borderRadius:"2px" }}></div>
                <div style={{ width:"16px", height:"1.5px", background:"#fff", borderRadius:"2px" }}></div>
              </div>
            </button>
          )}
          <div style={{ color:"#111", fontWeight:"700", fontSize:"16px" }}>{TABS.find(t=>t.key===tab)?.label}</div>
        </div>

        <div style={s.content}>
          {msg && <div className="anim" style={s.successMsg}>{msg}</div>}

          {tab==="entries" && (
            <div className="anim">
              <div style={dash.sectionHeader}>
                <div><div style={dash.sectionTitle}>Knowledge Base</div><div style={dash.sectionSub}>{entries.filter(e=>e.active).length} active entries</div></div>
                <button className="pill-btn glow-btn" onClick={()=>setTab("add")} style={dash.primaryBtn}>+ Add Entry</button>
              </div>
              {loading ? <div style={s.loadingText}>Loading...</div> : entries.filter(e=>e.active).map(e => {
                const tc = TOPIC_COLORS[e.topic] || TOPIC_COLORS.general;
                return (
                  <div key={e.id} className="entry-card" style={dash.card}>
                    <span style={{ background:tc.bg, color:tc.color, fontSize:"9px", fontWeight:"800", padding:"3px 12px", borderRadius:"25px", textTransform:"uppercase", letterSpacing:"0.8px" }}>{e.topic}</span>
                    <div style={{ fontWeight:"600", color:"#111", fontSize:"14px", marginTop:"10px", marginBottom:"4px" }}>{e.question}</div>
                    <div style={{ color:"#888", fontSize:"13px", lineHeight:"1.6" }}>{e.answer}</div>
                    <div style={{ display:"flex", gap:"8px", marginTop:"12px" }}>
                      <button className="pill-btn" onClick={()=>startEdit(e)} style={dash.primaryBtn}>Edit</button>
                      <button className="pill-btn pill-outline" onClick={()=>deleteEntry(e.id)} style={dash.outlineBtn}>Deactivate</button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {tab==="add" && (
            <div className="anim">
              <div style={dash.sectionHeader}>
                <div><div style={dash.sectionTitle}>{editId?"Edit Entry":"Add New Entry"}</div><div style={dash.sectionSub}>Fill in all required fields</div></div>
              </div>
              <div style={dash.card}>
                <select style={dash.input} value={form.topic} onChange={e=>setForm({...form,topic:e.target.value})}>
                  <option value="">Select topic</option>
                  {["fees","registration","exams","hostel","enrollment","general"].map(t=>(
                    <option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>
                  ))}
                </select>
                <input style={dash.input} placeholder="Question" value={form.question} onChange={e=>setForm({...form,question:e.target.value})} />
                <textarea style={{...dash.input,height:"120px",resize:"vertical"}} placeholder="Answer" value={form.answer} onChange={e=>setForm({...form,answer:e.target.value})} />
                <input style={dash.input} placeholder="Keywords (optional)" value={form.keywords} onChange={e=>setForm({...form,keywords:e.target.value})} />
                <div style={{ display:"flex", gap:"10px" }}>
                  <button className="pill-btn glow-btn" onClick={saveEntry} style={dash.primaryBtn}>{editId?"Update Entry":"Save Entry"}</button>
                  {editId && <button className="pill-btn pill-outline" onClick={()=>{setEditId(null);setForm({topic:"",question:"",answer:"",keywords:""})}} style={dash.outlineBtn}>Cancel</button>}
                </div>
              </div>
            </div>
          )}

          {tab==="logs" && (
            <div className="anim">
              <div style={dash.sectionHeader}>
                <div><div style={dash.sectionTitle}>Chat Logs</div><div style={dash.sectionSub}>{logs.length} recent conversations</div></div>
              </div>
              {loading ? <div style={s.loadingText}>Loading...</div> : logs.map((l,i) => {
                const tc = TOPIC_COLORS[l.topic] || TOPIC_COLORS.general;
                return (
                  <div key={i} className="entry-card" style={dash.card}>
                    <span style={{ background:tc.bg, color:tc.color, fontSize:"9px", fontWeight:"800", padding:"3px 12px", borderRadius:"25px", textTransform:"uppercase", letterSpacing:"0.8px" }}>{l.topic}</span>
                    <div style={{ fontWeight:"600", color:"#111", fontSize:"14px", marginTop:"10px", marginBottom:"4px" }}>Q: {l.question}</div>
                    <div style={{ color:"#888", fontSize:"13px", lineHeight:"1.6" }}>A: {l.answer?.slice(0,200)}{l.answer?.length>200?"...":""}</div>
                  </div>
                );
              })}
            </div>
          )}

          {tab==="stats" && (
            <div className="anim">
              <div style={dash.sectionHeader}>
                <div><div style={dash.sectionTitle}>Analytics</div><div style={dash.sectionSub}>Usage and satisfaction overview</div></div>
              </div>
              {loading ? <div style={s.loadingText}>Loading...</div> : (
                <div>
                  <div style={s.statGrid}>
                    <div style={s.statCard}>
                      <div style={s.statNum}>{stats.total_questions||0}</div>
                      <div style={s.statLabel}>Total Questions</div>
                    </div>
                    {stats.feedback && (<>
                      <div style={{...s.statCard,background:"linear-gradient(135deg,#4ade80,#22c55e)"}}>
                        <div style={s.statNum}>👍 {stats.feedback.thumbs_up}</div>
                        <div style={s.statLabel}>Helpful</div>
                      </div>
                      <div style={{...s.statCard,background:"linear-gradient(135deg,#f87171,#ef4444)"}}>
                        <div style={s.statNum}>👎 {stats.feedback.thumbs_down}</div>
                        <div style={s.statLabel}>Not Helpful</div>
                      </div>
                      <div style={{...s.statCard,background:`linear-gradient(135deg,${RED},${DARK_RED})`}}>
                        <div style={s.statNum}>{stats.feedback.satisfaction_rate}%</div>
                        <div style={s.statLabel}>Satisfaction</div>
                      </div>
                    </>)}
                  </div>
                  <div style={{...dash.sectionTitle,marginBottom:"14px"}}>Questions by Topic</div>
                  {Object.entries(stats.by_topic||{}).map(([topic,count]) => {
                    const tc = TOPIC_COLORS[topic] || TOPIC_COLORS.general;
                    return (
                      <div key={topic} style={{ display:"flex", alignItems:"center", gap:"12px", marginBottom:"10px" }}>
                        <span style={{ background:tc.bg, color:tc.color, fontSize:"10px", fontWeight:"700", padding:"3px 12px", borderRadius:"20px", textTransform:"capitalize", minWidth:"90px", textAlign:"center" }}>{topic}</span>
                        <div style={{ flex:1, background:"#f0f0f0", borderRadius:"20px", height:"10px", overflow:"hidden" }}>
                          <div style={{ height:"100%", background:`linear-gradient(135deg,${RED},${DARK_RED})`, borderRadius:"20px", width:`${Math.min((count/(stats.total_questions||1))*100,100)}%`, transition:"width 0.5s" }} />
                        </div>
                        <span style={{ fontSize:"13px", color:"#777", minWidth:"24px", textAlign:"right", fontWeight:"600" }}>{count}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {tab==="upload" && <UploadTab api={API} secret={adminSecret} onSave={loadEntries} />}
          {tab==="settings" && <SettingsTab secret={adminSecret} />}
        </div>
      </div>
    </div>
  );
}

const s = {
  page:{ display:"flex", width:"100vw", height:"100dvh", background:"#f8f9ff", fontFamily:"-apple-system,'Segoe UI',sans-serif", overflow:"hidden" },
  overlay:{ position:"fixed", inset:0, background:"rgba(0,0,0,0.55)", zIndex:299, backdropFilter:"blur(2px)" },
  loginPage:{ display:"flex", alignItems:"center", justifyContent:"center", width:"100vw", height:"100dvh", background:`linear-gradient(135deg,${RED},${DARK_RED})`, fontFamily:"-apple-system,'Segoe UI',sans-serif", position:"relative", overflow:"hidden" },
  loginDecor1:{ position:"absolute", top:"-80px", right:"-80px", width:"300px", height:"300px", background:"rgba(255,255,255,0.06)", borderRadius:"50%", pointerEvents:"none" },
  loginDecor2:{ position:"absolute", bottom:"-100px", left:"-50px", width:"250px", height:"250px", background:"rgba(255,255,255,0.04)", borderRadius:"50%", pointerEvents:"none" },
  loginBox:{ background:"#fff", borderRadius:"24px", padding:"40px 36px", width:"100%", maxWidth:"380px", textAlign:"center", boxShadow:"0 24px 60px rgba(0,0,0,0.3)", zIndex:1 },
  loginLogoWrap:{ width:"64px", height:"64px", margin:"0 auto 16px", borderRadius:"16px", overflow:"hidden" },
  loginTitle:{ color:RED, fontWeight:"800", fontSize:"22px", letterSpacing:"0.3px", margin:"0 0 4px" },
  loginSub:{ color:"#aaa", fontSize:"13px", marginBottom:"24px" },
  loginInput:{ width:"100%", border:`2px solid rgba(192,0,42,0.15)`, borderRadius:"14px", padding:"12px 16px", fontSize:"14px", marginBottom:"12px", boxSizing:"border-box", fontFamily:"inherit", outline:"none", background:"#fff9fa" },
  loginError:{ color:"#ef4444", marginBottom:"12px", fontSize:"13px" },
  loginBtn:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, color:"#fff", border:"none", borderRadius:"14px", padding:"13px 24px", fontSize:"15px", cursor:"pointer", width:"100%", fontWeight:"700", letterSpacing:"0.3px" },
  sidebar:{ background:`linear-gradient(160deg,${RED} 0%,${DARK_RED} 100%)`, display:"flex", flexDirection:"column", padding:"20px 10px 16px", overflow:"hidden", boxShadow:"4px 0 20px rgba(0,0,0,0.15)" },
  sidebarHeader:{ display:"flex", alignItems:"center", justifyContent:"space-between", gap:"10px", marginBottom:"20px", paddingBottom:"16px", borderBottom:"1px solid rgba(255,255,255,0.1)" },
  sidebarLogoWrap:{ width:"40px", height:"40px", background:"#fff", borderRadius:"12px", padding:"5px", boxShadow:"0 4px 12px rgba(0,0,0,0.2)", flexShrink:0, boxSizing:"border-box", overflow:"hidden" },
  toggleBtn:{ background:"rgba(255,255,255,0.1)", border:"none", borderRadius:"10px", width:"34px", height:"34px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", flexShrink:0, transition:"background 0.2s" },
  navBtn:{ display:"flex", alignItems:"center", width:"100%", background:"transparent", border:"none", borderLeft:"4px solid transparent", borderRadius:"0 14px 14px 0", cursor:"pointer", textAlign:"left", marginBottom:"3px" },
  signOutBtn:{ background:"transparent", border:"1px solid rgba(255,255,255,0.12)", borderRadius:"12px", padding:"11px 16px", color:"rgba(255,255,255,0.35)", fontSize:"12px", cursor:"pointer", width:"100%", fontWeight:"600", letterSpacing:"0.3px", display:"flex", alignItems:"center", transition:"all 0.2s", marginTop:"8px" },
  main:{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden", minWidth:0 },
  topBar:{ background:"#fff", borderBottom:"1px solid rgba(0,0,0,0.06)", padding:"16px 20px", display:"flex", alignItems:"center", gap:"12px", flexShrink:0, boxShadow:"0 2px 8px rgba(0,0,0,0.04)" },
  mobileMenuBtn:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, border:"none", borderRadius:"10px", width:"36px", height:"36px", display:"flex", alignItems:"center", justifyContent:"center", cursor:"pointer", flexShrink:0 },
  content:{ flex:1, overflowY:"auto", padding:"20px" },
  successMsg:{ background:"linear-gradient(135deg,#d1fae5,#a7f3d0)", color:"#065f46", padding:"12px 18px", borderRadius:"12px", marginBottom:"16px", fontSize:"14px", fontWeight:"600" },
  loadingText:{ color:"#aaa", fontSize:"14px", padding:"20px 0" },
  statGrid:{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(140px,1fr))", gap:"12px", marginBottom:"24px" },
  statCard:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, borderRadius:"16px", padding:"20px", textAlign:"center", boxShadow:`0 4px 16px rgba(192,0,42,0.25)` },
  statNum:{ fontSize:"36px", fontWeight:"900", color:"#fff" },
  statLabel:{ fontSize:"12px", color:"rgba(255,255,255,0.75)", marginTop:"4px", letterSpacing:"0.3px" },
};

const dash = {
  sectionHeader:{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:"16px" },
  sectionTitle:{ fontSize:"18px", fontWeight:"700", color:"#111", letterSpacing:"0.2px" },
  sectionSub:{ fontSize:"12px", color:"#aaa", marginTop:"2px" },
  card:{ background:"#fff", borderRadius:"16px", padding:"16px 18px", marginBottom:"12px", border:"1px solid rgba(0,0,0,0.06)", boxShadow:"0 3px 12px rgba(0,0,0,0.05)" },
  input:{ display:"block", width:"100%", border:`2px solid rgba(192,0,42,0.12)`, borderRadius:"12px", padding:"11px 14px", fontSize:"14px", marginBottom:"12px", boxSizing:"border-box", fontFamily:"inherit", outline:"none", background:"#fff9fa", color:"#111" },
  primaryBtn:{ background:`linear-gradient(135deg,${RED},${DARK_RED})`, color:"#fff", border:"none", borderRadius:"25px", padding:"9px 22px", fontSize:"13px", cursor:"pointer", fontWeight:"700", letterSpacing:"0.3px", boxShadow:`0 3px 10px rgba(192,0,42,0.3)` },
  outlineBtn:{ background:"#fff", color:"#ef4444", border:"1.5px solid #fca5a5", borderRadius:"25px", padding:"9px 22px", fontSize:"13px", cursor:"pointer", fontWeight:"700", letterSpacing:"0.3px" },
};
