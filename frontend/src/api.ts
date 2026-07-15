/** API client. Token stored in localStorage; attached as Bearer. */

const TOKEN_KEY = "gb_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

const API = import.meta.env.VITE_API_BASE || "";

async function req(method: string, path: string, body?: unknown) {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) throw new Error("unauthorized");
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  register: (email: string, password: string) =>
    req("POST", "/api/v1/auth/register", { email, password }),
  login: (email: string, password: string) =>
    req("POST", "/api/v1/auth/login", { email, password }),
  me: () => req("GET", "/api/v1/auth/me"),
  listProjects: () => req("GET", "/api/v1/projects"),
  createProject: (p: unknown) => req("POST", "/api/v1/projects", p),
  availableTests: (pid: number) => req("GET", `/api/v1/projects/${pid}/tests/available`),
  runTest: (pid: number, testName: string) =>
    req("POST", `/api/v1/projects/${pid}/tests/run`, { test_name: testName }),
  listRuns: (pid: number) => req("GET", `/api/v1/projects/${pid}/test-runs`),
};
