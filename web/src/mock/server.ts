// In-app mock of the farm API, so the dashboard works with no backend.
// It answers the same paths and shapes as backend/api (issue #14).

const MAX_PUMP_S = 900;
let pumpUntil = 0;

function soilAt(ts: number) {
  // Dries ~0.25 %/5 min, watered back to 50 % whenever it hits 30 %.
  const cycle = 80 * 5 * 60;
  return 50 - ((ts % cycle) / cycle) * 20 + Math.sin(ts / 900) * 0.4;
}

function tempAt(ts: number) {
  const hour = new Date(ts * 1000).getHours() + new Date(ts * 1000).getMinutes() / 60;
  return 14 + 8 * Math.sin(((hour - 9) / 24) * 2 * Math.PI);
}

const SERIES: Record<string, (ts: number) => number> = {
  "irrigation-1:soil_moisture_pct": soilAt,
  "irrigation-1:air_temp_c": tempAt,
  "irrigation-1:air_humidity_pct": (ts) => 70 - 1.8 * (tempAt(ts) - 14),
  "irrigation-1:pump_on": (ts) => (ts < pumpUntil ? 1 : 0),
  "hive-1:hive_weight_kg": (ts) => 38 + ((ts / 86400) % 30) * 0.05,
  "hive-1:hive_temp_c": (ts) => 34.5 + Math.sin(ts / 1200) * 0.3,
  "coop-1:air_temp_c": (ts) => tempAt(ts) + 2,
};

function todayAt(hour: number) {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return Math.floor(d.getTime() / 1000);
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

export async function mockFetch(input: string, init: RequestInit = {}): Promise<Response> {
  await new Promise((r) => setTimeout(r, 150));
  const url = new URL(input, "http://mock");
  const now = Math.floor(Date.now() / 1000);
  const method = (init.method ?? "GET").toUpperCase();
  const authed = new Headers(init.headers).get("Authorization")?.startsWith("Bearer ");

  if (url.pathname === "/api/login" && method === "POST") {
    const { username, password } = JSON.parse(String(init.body ?? "{}"));
    // Any non-empty credentials work in the demo.
    if (!username || !password) return json({ detail: "Wrong username or password" }, 401);
    return json({ token: "mock-token", expires: now + 30 * 86400 });
  }
  if (!authed) return json({ detail: "Missing or invalid token" }, 401);

  if (url.pathname === "/api/nodes") {
    const latest = (node: string) =>
      Object.fromEntries(
        Object.entries(SERIES)
          .filter(([key]) => key.startsWith(`${node}:`))
          .map(([key, f]) => [key.split(":")[1], Math.round(f(now) * 10) / 10]),
      );
    return json([
      { id: "irrigation-1", status: "online", last_seen: now - 20, latest: { ...latest("irrigation-1"), battery_v: 4.1 } },
      { id: "hive-1", status: "online", last_seen: now - 45, latest: { ...latest("hive-1"), battery_v: 3.9 } },
      { id: "coop-1", status: "offline", last_seen: now - 3 * 3600, latest: { ...latest("coop-1"), battery_v: 3.4 } },
    ]);
  }

  if (url.pathname === "/api/readings") {
    const f = SERIES[`${url.searchParams.get("node")}:${url.searchParams.get("metric")}`];
    const to = Number(url.searchParams.get("to") ?? now);
    const from = Number(url.searchParams.get("from") ?? to - 86400);
    if (!f) return json([]);
    const out = [];
    for (let ts = from - (from % 300) + 300; ts <= to; ts += 300) out.push({ ts, value: Math.round(f(ts) * 10) / 10 });
    return json(out);
  }

  if (url.pathname === "/api/events") {
    const events = [
      { ts: todayAt(7), node: "coop-1", type: "door", state: "open" },
      { ts: todayAt(19), node: "coop-1", type: "door", state: "closed" },
      { ts: todayAt(6) + 1800, node: "irrigation-1", type: "pump", state: "started", reason: "auto", duration_s: 300 },
      { ts: todayAt(6) + 2100, node: "irrigation-1", type: "pump", state: "stopped", reason: "done" },
      { ts: todayAt(19) - 86400, node: "coop-1", type: "door", state: "closed" },
    ]
      .filter((e) => e.ts <= now)
      .filter((e) => !url.searchParams.get("node") || e.node === url.searchParams.get("node"))
      .filter((e) => !url.searchParams.get("type") || e.type === url.searchParams.get("type"))
      .sort((a, b) => b.ts - a.ts);
    return json(events.slice(0, Number(url.searchParams.get("limit") ?? 50)));
  }

  const pump = url.pathname.match(/^\/api\/nodes\/([^/]+)\/pump$/);
  if (pump && method === "POST") {
    if (pump[1] !== "irrigation-1") return json({ detail: `${pump[1]} has no pump` }, 404);
    const { duration_s } = JSON.parse(String(init.body ?? "{}"));
    const capped = Math.min(Number(duration_s), MAX_PUMP_S);
    pumpUntil = now + capped;
    return json({ ok: true, duration_s: capped }, 202);
  }

  return json({ detail: "Not found" }, 404);
}
