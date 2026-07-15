import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      // try login first; if unknown, register then login
      let r = await api.login(email, password).catch(() => null);
      if (!r) {
        await api.register(email, password);
        r = await api.login(email, password);
      }
      setToken(r.access_token);
      nav("/");
    } catch {
      setErr("Auth failed. Check credentials.");
    }
  }

  return (
    <div style={wrap}>
      <h1>GameBridge AI</h1>
      <p>Game-commerce API diagnosis &amp; verification</p>
      <form onSubmit={submit} style={form}>
        <input style={input} placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input style={input} type="password" placeholder="password (min 8)" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button style={btn} type="submit">Sign in / Register</button>
        {err && <span style={{ color: "red" }}>{err}</span>}
      </form>
    </div>
  );
}

const wrap: React.CSSProperties = { maxWidth: 420, margin: "10vh auto", fontFamily: "system-ui" };
const form: React.CSSProperties = { display: "flex", flexDirection: "column", gap: 10 };
const input: React.CSSProperties = { padding: 10, borderRadius: 6, border: "1px solid #ccc" };
const btn: React.CSSProperties = { padding: 10, borderRadius: 6, border: 0, background: "#2563eb", color: "white", cursor: "pointer" };
