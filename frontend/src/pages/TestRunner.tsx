import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

interface Trace { method: string; url: string; request_headers: Record<string, string>; request_body: unknown; response_status: number | null; response_headers: Record<string, string>; response_body: unknown; duration_ms: number; status: string; }
interface RunResult { test_run_id: number; passed: boolean; detail: string; trace: Trace; }
interface Diagnosis { diagnosis_id: number; problem: string; root_cause: string; evidence: string[]; confidence: number; }
interface Fix { id: number; fix_type: string; description: string; code: string; verification_test: string; }
interface Verify { verification_run_id: number; status: string; rerun_response_status: number | null; notes: string; }

export default function TestRunner() {
  const { id } = useParams();
  const pid = Number(id);
  const [tests, setTests] = useState<string[]>([]);
  const [result, setResult] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [diag, setDiag] = useState<Diagnosis | null>(null);
  const [fixes, setFixes] = useState<Fix[]>([]);
  const [verify, setVerify] = useState<Verify | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.availableTests(pid).then((t: { name: string }[]) => setTests(t.map((x) => x.name)));
  }, [pid]);

  async function run(name: string) {
    setBusy(true); setError(null);
    setResult(null); setDiag(null); setFixes([]); setVerify(null);
    try {
      const r = await api.runTest(pid, name);
      setResult(r);
    } catch (e: unknown) { setError(String(e)); }
    finally { setBusy(false); }
  }

  async function diagnose() {
    if (!result) return;
    setBusy(true); setError(null); setDiag(null); setFixes([]); setVerify(null);
    try {
      const d = await api.diagnose(pid, result.test_run_id);
      setDiag(d);
    } catch (e: unknown) { setError(String(e)); }
    finally { setBusy(false); }
  }

  async function genFixes() {
    if (!diag) return;
    setBusy(true); setError(null); setFixes([]); setVerify(null);
    try {
      const f = await api.fixes(pid, diag.diagnosis_id);
      setFixes(f);
    } catch (e: unknown) { setError(String(e)); }
    finally { setBusy(false); }
  }

  async function doVerify(fixId: number) {
    setBusy(true); setError(null); setVerify(null);
    try {
      const v = await api.verify(pid, fixId);
      setVerify(v);
    } catch (e: unknown) { setError(String(e)); }
    finally { setBusy(false); }
  }

  return (
    <div style={wrap}>
      <h2>Test Runner — Project {pid}</h2>
      <p style={{ color: "#475569", fontSize: 14 }}>
        Run a failing integration test, then Diagnose → Suggest Fix → Verify. The AI is never
        trusted until a deterministic test proves the fix.
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {tests.map((t) => (
          <button key={t} style={btn} disabled={busy} onClick={() => run(t)}>{t}</button>
        ))}
      </div>

      {error && <div style={{ ...box, background: "#fee2e2", color: "#991b1b" }}>{error}</div>}
      {busy && <p>Working… (AI calls run locally on Ollama, ~10–30s each)</p>}

      {result && <TraceViewer result={result} onDiagnose={diagnose} busy={busy} />}
      {diag && <DiagnosisCard diag={diag} onFixes={genFixes} busy={busy} />}
      {fixes.length > 0 && (
        <FixList fixes={fixes} onVerify={doVerify} verify={verify} busy={busy} />
      )}
    </div>
  );
}

function TraceViewer({ result, onDiagnose, busy }: { result: RunResult; onDiagnose: () => void; busy: boolean }) {
  const t = result.trace;
  const passColor = result.passed ? "#16a34a" : "#dc2626";
  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ padding: 12, borderRadius: 8, background: passColor, color: "white" }}>
        <strong>{result.passed ? "TEST PASSED" : "TEST FAILED"}</strong> — {result.detail}
      </div>
      <h4>Request</h4>
      <pre style={code}>{`${t.method} ${t.url}`}</pre>
      <pre style={code}>{JSON.stringify(t.request_headers, null, 2)}</pre>
      <h4>Response</h4>
      <pre style={code}>status: {t.response_status} ({t.duration_ms} ms)</pre>
      <pre style={code}>{JSON.stringify(t.response_body, null, 2)}</pre>
      {!result.passed && (
        <button style={{ ...btn, background: "#2563eb", color: "white" }} disabled={busy} onClick={onDiagnose}>
          🔍 Diagnose with AI
        </button>
      )}
    </div>
  );
}

function DiagnosisCard({ diag, onFixes, busy }: { diag: Diagnosis; onFixes: () => void; busy: boolean }) {
  return (
    <div style={{ ...box, marginTop: 24, borderLeft: "4px solid #7c3aed" }}>
      <h3 style={{ marginTop: 0 }}>🧠 AI Diagnosis</h3>
      <p><strong>Problem:</strong> {diag.problem}</p>
      <p><strong>Root cause:</strong> {diag.root_cause}</p>
      <p><strong>Confidence:</strong> {(diag.confidence * 100).toFixed(0)}%</p>
      <p><strong>Evidence:</strong></p>
      <ul>{diag.evidence.map((e, i) => <li key={i} style={{ fontSize: 13 }}>{e}</li>)}</ul>
      <button style={{ ...btn, background: "#7c3aed", color: "white" }} disabled={busy} onClick={onFixes}>
        💡 Suggest Fix
      </button>
    </div>
  );
}

function FixList({ fixes, onVerify, verify, busy }: { fixes: Fix[]; onVerify: (id: number) => void; verify: Verify | null; busy: boolean }) {
  return (
    <div style={{ ...box, marginTop: 24, borderLeft: "4px solid #0891b2" }}>
      <h3 style={{ marginTop: 0 }}>🛠 Suggested Fixes</h3>
      {fixes.map((f) => (
        <div key={f.id} style={{ padding: 12, background: "#f1f5f9", borderRadius: 8, marginBottom: 12 }}>
          <p><strong>[{f.fix_type}]</strong> {f.description}</p>
          {f.code && <pre style={code}>{f.code}</pre>}
          <p style={{ fontSize: 13, color: "#475569" }}>Verification test: <code>{f.verification_test}</code></p>
          <button style={{ ...btn, background: "#0891b2", color: "white" }} disabled={busy} onClick={() => onVerify(f.id)}>
            ✅ Verify (rerun test)
          </button>
        </div>
      ))}
      {verify && (
        <div style={{ ...box, marginTop: 8, background: verify.status === "verified" ? "#dcfce7" : "#fee2e2", color: verify.status === "verified" ? "#166534" : "#991b1b" }}>
          <strong>{verify.status === "verified" ? "✔ VERIFIED" : "✘ NOT VERIFIED"}</strong> — {verify.notes}
        </div>
      )}
    </div>
  );
}

const wrap: React.CSSProperties = { maxWidth: 820, margin: "0 auto", padding: 24, fontFamily: "system-ui" };
const btn: React.CSSProperties = { padding: "8px 12px", borderRadius: 6, border: "1px solid #2563eb", background: "white", color: "#2563eb", cursor: "pointer" };
const code: React.CSSProperties = { background: "#0f172a", color: "#e2e8f0", padding: 12, borderRadius: 6, overflowX: "auto", fontSize: 13 };
const box: React.CSSProperties = { padding: 16, borderRadius: 8, background: "white", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" };
