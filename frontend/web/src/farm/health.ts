// Plant health risks from the farm's own temperature and humidity readings.
// Simple, well-known rules of thumb: they say when to look closely, not what the plant has.
import type { Reading } from "../api";

export type Level = "low" | "medium" | "high";

export type HourClimate = { hour: number; temp: number; rh: number }; // hour = unix seconds at the start of the hour

/** Averages temperature and humidity readings into whole hours that have both. */
export function hourly(temps: Reading[], hums: Reading[]): HourClimate[] {
  const bucket = (rs: Reading[]) => {
    const m = new Map<number, { sum: number; n: number }>();
    for (const r of rs) {
      const h = r.ts - (r.ts % 3600);
      const b = m.get(h) ?? { sum: 0, n: 0 };
      b.sum += r.value;
      b.n += 1;
      m.set(h, b);
    }
    return m;
  };
  const t = bucket(temps);
  const h = bucket(hums);
  const out: HourClimate[] = [];
  for (const [hour, tb] of t) {
    const hb = h.get(hour);
    if (hb) out.push({ hour, temp: tb.sum / tb.n, rh: hb.sum / hb.n });
  }
  return out.sort((a, b) => a.hour - b.hour);
}

/** Leaf wetness proxy: humid enough for fungal spores to germinate (late blight, downy mildew). */
export function isWetHour(h: HourClimate) {
  return h.rh >= 90 && h.temp >= 10 && h.temp <= 25;
}

/** Warm and moderately humid, the conditions powdery mildew likes (it does not need wet leaves). */
export function isMildewHour(h: HourClimate) {
  return h.temp >= 20 && h.temp <= 30 && h.rh >= 40 && h.rh <= 80;
}

/**
 * Fungal risk over the last 3 days. Like the Smith period used for late blight warnings:
 * a day with 11 or more humid hours is high risk, 6 or more is medium.
 */
export function fungalRisk(hours: HourClimate[], now: number): { level: Level; worstDayHours: number } {
  const perDay = [0, 0, 0];
  for (const h of hours) {
    const age = Math.floor((now - h.hour) / 86400);
    if (age >= 0 && age < 3 && isWetHour(h)) perDay[age] += 1;
  }
  const worst = Math.max(...perDay);
  return { level: worst >= 11 ? "high" : worst >= 6 ? "medium" : "low", worstDayHours: worst };
}

export function mildewRisk(hours: HourClimate[], now: number): { level: Level; hours: number } {
  const recent = hours.filter((h) => now - h.hour < 3 * 86400);
  const n = recent.filter(isMildewHour).length;
  return { level: n >= 36 ? "high" : n >= 18 ? "medium" : "low", hours: n };
}

// Tuta absoluta (tomato leaf miner): development threshold 8.1 °C, about 460 degree-days per generation.
export const TUTA_BASE_C = 8.1;
export const TUTA_GENERATION_DD = 460;

export function degreeDays(dailyMeans: { date: string; tMean: number }[], since: string, base = TUTA_BASE_C) {
  return dailyMeans.filter((d) => d.date >= since).reduce((s, d) => s + Math.max(0, d.tMean - base), 0);
}

export function tutaStatus(dd: number) {
  const generations = Math.floor(dd / TUTA_GENERATION_DD);
  const intoGeneration = dd - generations * TUTA_GENERATION_DD;
  // Last 15 % of a generation: adults are about to emerge, the moment to check traps.
  return { dd, generations, progress: intoGeneration / TUTA_GENERATION_DD, checkTraps: intoGeneration >= 0.85 * TUTA_GENERATION_DD };
}
