import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";

interface Trace { method: string; url: string; request_headers: Record<string, string>; request_body: unknown; response_status: number | null; response_headers: Record<string, string>; response_body: unknown; duration_ms: number; status: string; }
interface RunResult { test_run_id: number; passed: boolean; detail: string; trace: Trace; }

export default function TestRunner() {
  const { id } = useParams();
  const pid = Number(id);
  const [tests, setTests] = useState<string[]>([]);
  const [result, setResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api.availableTests(pid).then((t: { name: string }[]) => setTests(t.map((x) => x.name)));
  }, [pid]);

  async function run(name: string) {
    setRunning(true);
    setResult(null);
    try {
      const r = await api.runTest(pid, name);
      setResult(r);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div style={wrap}>
      <h2>Test Runner — Project {pid}</h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {tests.map((t) => (
          <button key={t} style={btn} disabled={running} onClick={() => run(t)}>{t}</button>
        ))}
      </div>
      {running && <p>Running…</p>}
      {result && <TraceViewer result={result} />}
    </div>
  );
}

function TraceViewer({ result }: { result: RunResult }) {
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
    </div>
  );
}

const wrap: React.CSSProperties = { maxWidth: 820, margin: "0 auto", padding: 24, fontFamily: "system-ui" };
const btn: React.CSSProperties = { padding: "8px 12px", borderRadius: 6, border: "1px solid #2563eb", background: "white", color: "#2563eb", cursor: "pointer" };
const code: React.CSSProperties = { background: "#0f172a", color: "#e2e8f0", padding: 12, borderRadius: 6, overflowX: "auto", fontSize: 13 };
