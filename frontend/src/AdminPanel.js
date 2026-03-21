import { useState } from "react";

const BACKEND = process.env.REACT_APP_BACKEND_URL || "https://student-assistant-backend-etbm.onrender.com";
const ADMIN_PASSWORD = "acitystudentassistant2025";

export default function AdminPanel() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [questions, setQuestions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newQ, setNewQ] = useState("");
  const [newA, setNewA] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  const handleLogin = (e) => {
    e.preventDefault();
    if (password === ADMIN_PASSWORD) {
      setAuthenticated(true);
      setError("");
      loadData();
    } else {
      setError("Incorrect password. Try again.");
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [kbRes, analyticsRes] = await Promise.all([
        fetch(`${BACKEND}/admin/entries`),
        fetch(`${BACKEND}/admin/stats`)
      ]);
      if (kbRes.ok) setQuestions(await kbRes.json());
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
    } catch (err) {
      console.error("Failed to load admin data:", err);
    }
    setLoading(false);
  };

  const handleAddQA = async (e) => {
    e.preventDefault();
    setSaveMsg("");
    try {
      const res = await fetch(`${BACKEND}/admin/entries`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Secret-Key": ADMIN_PASSWORD
        },
        body: JSON.stringify({ question: newQ, answer: newA, topic: "general", keywords: [] })
      });
      if (res.ok) {
        setSaveMsg("Saved successfully!");
        setNewQ("");
        setNewA("");
        loadData();
      } else {
        setSaveMsg("Failed to save.");
      }
    } catch {
      setSaveMsg("Cannot reach backend.");
    }
  };

  if (!authenticated) {
    return (
      <div style={styles.loginPage}>
        <div style={styles.loginBox}>
          <h2>Admin Login</h2>
          <p>ACity Student Assistant</p>
          <form onSubmit={handleLogin}>
            <input
              type="password"
              placeholder="Enter admin password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              style={styles.input}
            />
            {error && <p style={{ color: "red" }}>{error}</p>}
            <button type="submit" style={styles.btn}>Login</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.dashboard}>
      <h1>Admin Dashboard</h1>
      {analytics && (
        <div style={styles.card}>
          <h3>Analytics</h3>
          <p>Total questions asked: <strong>{analytics.total_questions || 0}</strong></p>
          <p>Knowledge base entries: <strong>{analytics.kb_count || questions.length}</strong></p>
        </div>
      )}
      <div style={styles.card}>
        <h3>Add Knowledge Base Entry</h3>
        <form onSubmit={handleAddQA}>
          <input
            placeholder="Question"
            value={newQ}
            onChange={e => setNewQ(e.target.value)}
            style={{ ...styles.input, width: "100%" }}
            required
          />
          <textarea
            placeholder="Answer"
            value={newA}
            onChange={e => setNewA(e.target.value)}
            style={{ ...styles.input, width: "100%", height: 80 }}
            required
          />
          <button type="submit" style={styles.btn}>Save Entry</button>
          {saveMsg && <span style={{ marginLeft: 12 }}>{saveMsg}</span>}
        </form>
      </div>
      <div style={styles.card}>
        <h3>Knowledge Base ({questions.length} entries)</h3>
        {loading ? <p>Loading...</p> : questions.map((qa, i) => (
          <div key={i} style={styles.qaItem}>
            <strong>Q:</strong> {qa.question}<br />
            <span style={{ color: "#555" }}><strong>A:</strong> {qa.answer}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  loginPage: { display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "#f0f2f5" },
  loginBox: { background: "white", padding: 40, borderRadius: 12, boxShadow: "0 4px 20px rgba(0,0,0,0.1)", textAlign: "center", minWidth: 320 },
  dashboard: { maxWidth: 800, margin: "0 auto", padding: 24 },
  card: { background: "white", borderRadius: 12, padding: 20, marginBottom: 20, boxShadow: "0 2px 8px rgba(0,0,0,0.08)" },
  input: { display: "block", padding: "10px 14px", margin: "8px 0", borderRadius: 8, border: "1px solid #ddd", fontSize: 14 },
  btn: { background: "#4f46e5", color: "white", border: "none", padding: "10px 24px", borderRadius: 8, cursor: "pointer", marginTop: 8 },
  qaItem: { borderBottom: "1px solid #eee", padding: "10px 0", fontSize: 14 }
};
