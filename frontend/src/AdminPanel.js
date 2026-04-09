import { useState } from "react";

// Must match REACT_APP_BACKEND_URL in your .env
const BACKEND =
  process.env.REACT_APP_BACKEND_URL ||
  "https://student-assistant-backend-etbm.onrender.com";

// Must match SECRET_KEY on your backend .env
const ADMIN_PASSWORD = "acitystudentassistant2025";

export default function AdminPanel() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword]           = useState("");
  const [loginError, setLoginError]       = useState("");

  const [entries, setEntries]   = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading]   = useState(false);

  // Add-entry form
  const [newTopic, setNewTopic] = useState("general");
  const [newQ, setNewQ]         = useState("");
  const [newA, setNewA]         = useState("");
  const [saveMsg, setSaveMsg]   = useState("");

  // Refresh knowledge base
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMsg, setRefreshMsg] = useState("");

  // ── Auth header used on every admin request ───────────────
  const adminHeaders = {
    "Content-Type": "application/json",
    "X-Admin-Key": ADMIN_PASSWORD,   // backend checks this header
  };

  // ── Load KB entries + analytics ──────────────────────────
  const loadData = async () => {
    setLoading(true);
    try {
      const [kbRes, statsRes] = await Promise.all([
        fetch(`${BACKEND}/admin/entries`, { headers: adminHeaders }),
        fetch(`${BACKEND}/admin/stats`,   { headers: adminHeaders }),
      ]);
      if (kbRes.ok) {
        const kbData = await kbRes.json();
        setEntries(kbData.entries || []);
      }
      if (statsRes.ok) {
        setAnalytics(await statsRes.json());
      }
    } catch (err) {
      console.error("Failed to load admin data:", err);
    }
    setLoading(false);
  };

  // ── Login ────────────────────────────────────────────────
  const handleLogin = (e) => {
    e.preventDefault();
    if (password === ADMIN_PASSWORD) {
      setAuthenticated(true);
      setLoginError("");
      loadData();
    } else {
      setLoginError("Incorrect password. Please try again.");
    }
  };

  // ── Add KB entry ─────────────────────────────────────────
  const handleAddEntry = async (e) => {
    e.preventDefault();
    setSaveMsg("");
    try {
      const res = await fetch(`${BACKEND}/admin/entries`, {
        method: "POST",
        headers: adminHeaders,
        body: JSON.stringify({
          admin_key: ADMIN_PASSWORD, // also in body for belt-and-braces
          topic:    newTopic,
          question: newQ,
          answer:   newA,
          keywords: "",
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSaveMsg("✅ Entry saved successfully!");
        setNewQ("");
        setNewA("");
        setNewTopic("general");
        loadData();
      } else {
        setSaveMsg("❌ " + (data.error || "Failed to save."));
      }
    } catch {
      setSaveMsg("❌ Cannot reach the backend.");
    }
  };

  // ── Delete (deactivate) KB entry ─────────────────────────
  const handleDeleteEntry = async (id) => {
    if (!window.confirm("Deactivate this entry? It won't be deleted permanently.")) return;
    try {
      await fetch(`${BACKEND}/admin/entries/${id}`, {
        method: "DELETE",
        headers: adminHeaders,
      });
      loadData();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // ── Trigger remote knowledge base refresh ────────────────
  // Calls POST /admin/refresh-knowledge on the backend.
  // The backend runs refresh_knowledge.py in a background thread
  // and responds immediately — scraping takes 5-10 min in the background.
  const triggerKnowledgeRefresh = async () => {
    setRefreshing(true);
    setRefreshMsg("");
    try {
      const res = await fetch(`${BACKEND}/admin/refresh-knowledge`, {
        method: "POST",
        headers: adminHeaders,
        body: JSON.stringify({ admin_key: ADMIN_PASSWORD }),
      });
      const data = await res.json();
      if (res.ok) {
        setRefreshMsg("🚀 " + (data.message || "Refresh started."));
      } else {
        setRefreshMsg("❌ " + (data.error || "Something went wrong."));
      }
    } catch (e) {
      setRefreshMsg("❌ Request failed: " + e.message);
    }
    setRefreshing(false);
  };

  // ── Login screen ─────────────────────────────────────────
  if (!authenticated) {
    return (
      <div style={st.loginPage}>
        <div style={st.loginBox}>
          <div style={{ fontSize: 52, marginBottom: 8 }}>🤖</div>
          <h2 style={{ margin: "0 0 4px", color: "#1a1a1a", fontSize: 22 }}>
            Kai Admin Panel
          </h2>
          <p style={{ margin: "0 0 22px", color: "#999", fontSize: 13 }}>
            ACity Student Assistant
          </p>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Enter admin password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={{ ...st.input, width: "100%", boxSizing: "border-box" }}
              autoFocus
            />
            {loginError && (
              <p style={{ color: "#c0002a", fontSize: 13, margin: "6px 0" }}>
                {loginError}
              </p>
            )}
            <button type="submit" style={{ ...st.btn, width: "100%", marginTop: 4 }}>
              Login →
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Dashboard ─────────────────────────────────────────────
  return (
    <div style={st.dashboard}>

      {/* Page header */}
      <div style={st.pageHeader}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, color: "#1a1a1a" }}>
            🤖 Kai Admin Dashboard
          </h1>
          <p style={{ margin: "4px 0 0", color: "#999", fontSize: 13 }}>
            ACity Student Assistant · Knowledge Base Manager
          </p>
        </div>
        <button
          onClick={loadData}
          style={{ ...st.btn, padding: "8px 18px", background: "#555" }}
        >
          ↻ Refresh Data
        </button>
      </div>

      {/* ── Analytics cards ── */}
      {analytics && (
        <div style={st.statsRow}>
          <div style={st.statCard}>
            <div style={st.statNum}>{analytics.total_questions || 0}</div>
            <div style={st.statLabel}>Questions Asked</div>
          </div>
          <div style={st.statCard}>
            <div style={st.statNum}>{entries.length}</div>
            <div style={st.statLabel}>KB Entries</div>
          </div>
          {analytics.feedback && (
            <>
              <div style={st.statCard}>
                <div style={{ ...st.statNum, color: "#16a34a" }}>
                  {analytics.feedback.thumbs_up || 0} 👍
                </div>
                <div style={st.statLabel}>Helpful Responses</div>
              </div>
              <div style={st.statCard}>
                <div style={{ ...st.statNum, color: "#c0002a" }}>
                  {analytics.feedback.satisfaction_rate || 0}%
                </div>
                <div style={st.statLabel}>Satisfaction Rate</div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Refresh Knowledge Base ── */}
      <div style={st.card}>
        <h3 style={st.cardTitle}>🔄 Refresh Knowledge Base</h3>
        <p style={{ color: "#666", fontSize: 13, margin: "0 0 14px", lineHeight: 1.6 }}>
          Scrapes all official ACity website pages and uses AI to extract fresh Q&amp;A pairs.
          Runs in the background — takes about <strong>5–10 minutes</strong> to complete.
          Only auto-generated entries are replaced; entries you add manually are never touched.
        </p>
        <button
          onClick={triggerKnowledgeRefresh}
          disabled={refreshing}
          style={{
            ...st.btn,
            background: refreshing ? "#aaa" : "#1a73e8",
            cursor: refreshing ? "not-allowed" : "pointer",
          }}
        >
          {refreshing ? "⏳ Starting..." : "🚀 Refresh Now"}
        </button>
        {refreshMsg && (
          <p
            style={{
              marginTop: 12,
              color: refreshMsg.startsWith("❌") ? "#c0002a" : "#16a34a",
              fontWeight: 500,
              fontSize: 13,
              lineHeight: 1.5,
            }}
          >
            {refreshMsg}
          </p>
        )}
      </div>

      {/* ── Add new KB entry ── */}
      <div style={st.card}>
        <h3 style={st.cardTitle}>➕ Add Knowledge Base Entry</h3>
        <form onSubmit={handleAddEntry}>
          <select
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            style={{ ...st.input, width: "100%", marginBottom: 8 }}
          >
            <option value="general">General</option>
            <option value="fees">Fees</option>
            <option value="registration">Registration</option>
            <option value="enrollment">Enrollment / Courses</option>
            <option value="exams">Exams &amp; Results</option>
            <option value="hostel">Hostel &amp; Campus Life</option>
          </select>
          <input
            placeholder="Question — e.g. How do I pay my fees?"
            value={newQ}
            onChange={(e) => setNewQ(e.target.value)}
            style={{ ...st.input, width: "100%", marginBottom: 8, boxSizing: "border-box" }}
            required
          />
          <textarea
            placeholder="Answer — write a clear, accurate response in plain text"
            value={newA}
            onChange={(e) => setNewA(e.target.value)}
            style={{
              ...st.input,
              width: "100%",
              height: 90,
              resize: "vertical",
              marginBottom: 10,
              boxSizing: "border-box",
            }}
            required
          />
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button type="submit" style={st.btn}>
              Save Entry
            </button>
            {saveMsg && (
              <span
                style={{
                  color: saveMsg.startsWith("✅") ? "#16a34a" : "#c0002a",
                  fontWeight: 500,
                  fontSize: 13,
                }}
              >
                {saveMsg}
              </span>
            )}
          </div>
        </form>
      </div>

      {/* ── Knowledge Base list ── */}
      <div style={st.card}>
        <h3 style={st.cardTitle}>
          📚 Knowledge Base{" "}
          <span style={{ fontWeight: 400, color: "#999", fontSize: 14 }}>
            ({entries.length} entries)
          </span>
        </h3>

        {loading ? (
          <p style={{ color: "#bbb", textAlign: "center", padding: 24 }}>Loading...</p>
        ) : entries.length === 0 ? (
          <p style={{ color: "#bbb", textAlign: "center", padding: 24 }}>
            No entries found.
          </p>
        ) : (
          entries.map((qa, i) => (
            <div key={qa.id || i} style={st.qaItem}>
              <div style={st.qaTopRow}>
                <span style={st.topicBadge}>{qa.topic || "general"}</span>
                {qa.source && (
                  <span style={st.sourceBadge}>{qa.source}</span>
                )}
                {qa.id && (
                  <button
                    onClick={() => handleDeleteEntry(qa.id)}
                    style={st.deleteBtn}
                    title="Deactivate entry"
                  >
                    ✕ Deactivate
                  </button>
                )}
              </div>
              <div style={{ fontWeight: 600, fontSize: 13, color: "#1a1a1a", marginBottom: 4 }}>
                Q: {qa.question}
              </div>
              <div style={{ fontSize: 13, color: "#555", lineHeight: 1.5 }}>
                A: {qa.answer}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────
const st = {
  loginPage: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    height: "100vh",
    background: "linear-gradient(135deg,#fff5f5,#fafafa)",
    fontFamily: "-apple-system,'Segoe UI',sans-serif",
  },
  loginBox: {
    background: "#fff",
    padding: "40px 44px",
    borderRadius: 18,
    boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
    textAlign: "center",
    minWidth: 340,
  },
  dashboard: {
    maxWidth: 880,
    margin: "0 auto",
    padding: "28px 20px 60px",
    fontFamily: "-apple-system,'Segoe UI',sans-serif",
  },
  pageHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 24,
    flexWrap: "wrap",
    gap: 12,
  },
  statsRow: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: 14,
    marginBottom: 20,
  },
  statCard: {
    background: "#fff",
    borderRadius: 12,
    padding: "16px 20px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
    border: "1px solid #f0f0f0",
  },
  statNum: {
    fontSize: 26,
    fontWeight: 700,
    color: "#c0002a",
    lineHeight: 1.2,
  },
  statLabel: {
    fontSize: 11,
    color: "#aaa",
    marginTop: 4,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.4px",
  },
  card: {
    background: "#fff",
    borderRadius: 14,
    padding: "22px 26px",
    marginBottom: 20,
    boxShadow: "0 2px 8px rgba(0,0,0,0.07)",
    border: "1px solid #f0f0f0",
  },
  cardTitle: {
    margin: "0 0 14px",
    fontSize: 15,
    fontWeight: 700,
    color: "#1a1a1a",
  },
  input: {
    display: "block",
    padding: "10px 14px",
    borderRadius: 8,
    border: "1.5px solid #e0e0e0",
    fontSize: 13,
    fontFamily: "inherit",
    outline: "none",
    background: "#fafafa",
  },
  btn: {
    background: "#c0002a",
    color: "#fff",
    border: "none",
    padding: "10px 22px",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
    fontFamily: "inherit",
  },
  qaItem: {
    borderBottom: "1px solid #f5f5f5",
    padding: "14px 0",
    fontSize: 13,
  },
  qaTopRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
    flexWrap: "wrap",
  },
  topicBadge: {
    display: "inline-block",
    background: "#fff5f5",
    color: "#c0002a",
    border: "1px solid rgba(192,0,42,0.2)",
    borderRadius: 20,
    padding: "2px 10px",
    fontSize: 11,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
  },
  sourceBadge: {
    display: "inline-block",
    background: "#f5f5f5",
    color: "#888",
    border: "1px solid #e0e0e0",
    borderRadius: 20,
    padding: "2px 8px",
    fontSize: 10,
    fontWeight: 600,
  },
  deleteBtn: {
    marginLeft: "auto",
    background: "transparent",
    border: "1px solid #e0e0e0",
    borderRadius: 6,
    color: "#bbb",
    cursor: "pointer",
    fontSize: 11,
    padding: "3px 10px",
    fontFamily: "inherit",
  },
};
