import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, clearToken } from "../api";

interface Project { id: number; name: string; framework: string; environment: string; }

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const nav = useNavigate();

  async function load() {
    try { setProjects(await api.listProjects()); } catch { clearToken(); nav("/login"); }
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!name) return;
    await api.createProject({ name, environment: "mock", framework: "fastapi" });
    setName("");
    load();
  }

  return (
    <div style={wrap}>
      <header style={head}>
        <h1>GameBridge AI</h1>
        <button style={linkBtn} onClick={() => { clearToken(); nav("/login"); }}>Logout</button>
      </header>
      <form onSubmit={create} style={{ display: "flex", gap: 8, margin: "16px 0" }}>
        <input style={input} placeholder="New project name" value={name} onChange={(e) => setName(e.target.value)} />
        <button style={btn} type="submit">Create</button>
      </form>
      <h3>Projects</h3>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {projects.map((p) => (
          <li key={p.id} style={card} onClick={() => nav(`/projects/${p.id}/tests`)}>
            <strong>{p.name}</strong> — {p.framework} / {p.environment}
          </li>
        ))}
        {projects.length === 0 && <li style={{ color: "#888" }}>No projects yet. Create one above.</li>}
      </ul>

      <details style={{ ...box, marginTop: 24 }}>
        <summary style={{ cursor: "pointer", fontWeight: 600 }}>How GameBridge works</summary>
        <div style={{ marginTop: 12 }}>
          <Flow />
          <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.5 }}>
            GameBridge runs deterministic integration tests against your game-commerce API (or the
            bundled mock). When a test fails, an LLM diagnoses the root cause from the real request/response
            trace and the API docs, then proposes a fix. Crucially, a fix is only marked <strong>verified</strong>{" "}
            after a deterministic test re-run proves it — the AI is never trusted on its word alone.
          </p>
        </div>
      </details>
    </div>
  );
}

function Flow() {
  const steps = ["Run test", "Capture trace", "AI diagnose", "Suggest fix", "Verify (rerun)"];
  return (
    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, margin: "8px 0" }}>
      {steps.map((s, i) => (
        <span key={s}>
          <span style={step}>{s}</span>
          {i < steps.length - 1 && <span style={{ color: "#94a3b8" }}> → </span>}
        </span>
      ))}
    </div>
  );
}

const wrap: React.CSSProperties = { maxWidth: 760, margin: "0 auto", padding: 24, fontFamily: "system-ui" };
const box: React.CSSProperties = { padding: 16, borderRadius: 8, background: "white", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" };
const head: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center" };
const input: React.CSSProperties = { padding: 10, borderRadius: 6, border: "1px solid #ccc", flex: 1 };
const btn: React.CSSProperties = { padding: "10px 16px", borderRadius: 6, border: 0, background: "#2563eb", color: "white", cursor: "pointer" };
const linkBtn: React.CSSProperties = { background: "none", border: "none", color: "#2563eb", cursor: "pointer" };
const card: React.CSSProperties = { padding: 14, border: "1px solid #e5e7eb", borderRadius: 8, marginBottom: 8, cursor: "pointer" };
const step: React.CSSProperties = { padding: "4px 8px", borderRadius: 6, background: "#2563eb", color: "white", fontSize: 12 };
