import type { TFunction } from "i18next";

const UNITS: Record<string, { unit: string; digits: number }> = {
  soil_moisture_pct: { unit: "%", digits: 0 },
  air_temp_c: { unit: "°C", digits: 1 },
  air_humidity_pct: { unit: "%", digits: 0 },
  water_liters: { unit: "L", digits: 0 },
  hive_weight_kg: { unit: "kg", digits: 1 },
  hive_temp_c: { unit: "°C", digits: 1 },
  battery_v: { unit: "V", digits: 2 },
};

export function formatMetric(metric: string, value: number, t: TFunction, lang: string): string {
  if (metric === "pump_on") return value ? t("bed.pumpOn") : t("bed.pumpOff");
  const u = UNITS[metric] ?? { unit: "", digits: 1 };
  const n = new Intl.NumberFormat(lang, { maximumFractionDigits: u.digits, minimumFractionDigits: u.digits }).format(value);
  return `${n} ${u.unit}`.trim();
}

export function timeAgo(ts: number | null, t: TFunction, now = Date.now() / 1000): string {
  if (!ts) return t("common.never");
  const s = Math.max(0, now - ts);
  if (s < 60) return t("common.justNow");
  if (s < 3600) return t("common.minutesAgo", { count: Math.floor(s / 60) });
  if (s < 86400) return t("common.hoursAgo", { count: Math.floor(s / 3600) });
  return t("common.daysAgo", { count: Math.floor(s / 86400) });
}

export function clockTime(ts: number, lang: string): string {
  return new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" }).format(new Date(ts * 1000));
}
