// Client for the farm API (backend/api, contract in issue #14).
// Switch from the mock to the real API by setting VITE_API_BASE.
import { mockFetch } from "./mock/server";

export type NodeInfo = {
  id: string;
  status: "online" | "offline";
  last_seen: number | null;
  latest: Record<string, number>;
};
export type Reading = { ts: number; value: number };
export type FarmEvent = { ts: number; node: string; type: string; state?: string; reason?: string; [k: string]: unknown };

const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true" || !BASE;
const TOKEN_KEY = "greenloop.token";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage blocked: the session lasts until the tab closes
  }
  window.dispatchEvent(new Event("greenloop:auth"));
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");
  const doFetch = USE_MOCK ? mockFetch : fetch;
  const res = await doFetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401 && !path.endsWith("/login")) setToken(null);
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json() as Promise<T>;
}

function query(params: Record<string, string | number | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; expires: number }>("/api/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  nodes: () => request<NodeInfo[]>("/api/nodes"),
  readings: (node: string, metric: string, from?: number, to?: number) =>
    request<Reading[]>(`/api/readings${query({ node, metric, from, to })}`),
  events: (params: { node?: string; type?: string; limit?: number } = {}) => request<FarmEvent[]>(`/api/events${query(params)}`),
  pump: (node: string, duration_s: number) =>
    request<{ ok: boolean; duration_s?: number }>(`/api/nodes/${encodeURIComponent(node)}/pump`, {
      method: "POST",
      body: JSON.stringify({ duration_s }),
    }),
};
