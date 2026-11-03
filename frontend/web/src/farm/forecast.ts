// Daily weather from Open-Meteo (free, no key), called from the browser so it works without our backend.
// The last good answer is kept on the device, so the plan still shows with no signal in the field.
import { USE_MOCK } from "../api";
import { load, save } from "./storage";
import type { DayWeather } from "./water";

export type Forecast = { fetchedAt: number; days: DayWeather[]; past: { date: string; tMean: number }[] };

const URL_BASE = "https://api.open-meteo.com/v1/forecast";
const KEY = "greenloop.forecast";
const PAST_DAYS = 92; // the most Open-Meteo gives; enough for Tuta absoluta degree-days

type OpenMeteoDaily = {
  daily: {
    time: string[];
    et0_fao_evapotranspiration: (number | null)[];
    precipitation_sum: (number | null)[];
    temperature_2m_max: (number | null)[];
    temperature_2m_min: (number | null)[];
    temperature_2m_mean: (number | null)[];
  };
};

export function forecastUrl(lat: number, lon: number) {
  const q = new URLSearchParams({
    latitude: String(lat),
    longitude: String(lon),
    daily: "et0_fao_evapotranspiration,precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean",
    timezone: "auto",
    past_days: String(PAST_DAYS),
    forecast_days: "7",
  });
  return `${URL_BASE}?${q}`;
}

export function parseForecast(body: OpenMeteoDaily, today: string, fetchedAt: number): Forecast {
  const d = body.daily;
  const days: DayWeather[] = [];
  const past: Forecast["past"] = [];
  d.time.forEach((date, i) => {
    const tMean = d.temperature_2m_mean[i];
    if (date < today) {
      if (tMean != null) past.push({ date, tMean });
      return;
    }
    days.push({
      date,
      et0: d.et0_fao_evapotranspiration[i] ?? 0,
      rainMm: d.precipitation_sum[i] ?? 0,
      tMax: d.temperature_2m_max[i] ?? NaN,
      tMin: d.temperature_2m_min[i] ?? NaN,
    });
    if (date === today && tMean != null) past.push({ date, tMean });
  });
  return { fetchedAt, days, past };
}

export function localDate(ms = Date.now()) {
  const d = new Date(ms);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** A plausible hot, dry week for demo mode (no network, no coordinates needed). */
export function mockForecast(now = Date.now()): Forecast {
  const days: DayWeather[] = [];
  const past: Forecast["past"] = [];
  for (let i = -PAST_DAYS; i < 7; i++) {
    const date = localDate(now + i * 86400_000);
    const tMax = 31 + 5 * Math.sin(i / 2) + (i === 2 ? 7 : 0);
    const tMin = tMax - 13;
    if (i <= 0) past.push({ date, tMean: 18 + 6 * Math.sin((i + 40) / 30) });
    if (i >= 0) days.push({ date, et0: 4.5 + 1.5 * Math.sin(i / 2) + (i === 2 ? 2 : 0), rainMm: i === 5 ? 6 : 0, tMax, tMin });
  }
  return { fetchedAt: now, days, past };
}

export async function getForecast(lat: number, lon: number, fetcher: typeof fetch = fetch): Promise<{ forecast: Forecast; cached: boolean }> {
  if (USE_MOCK) return { forecast: mockForecast(), cached: false };
  const cacheKey = `${KEY}.${lat.toFixed(2)},${lon.toFixed(2)}`;
  try {
    const res = await fetcher(forecastUrl(lat, lon));
    if (!res.ok) throw new Error(`Open-Meteo ${res.status}`);
    const forecast = parseForecast(await res.json(), localDate(), Date.now());
    save(cacheKey, forecast);
    return { forecast, cached: false };
  } catch (e) {
    const cached = load<Forecast | null>(cacheKey, null);
    if (cached && cached.days?.length) {
      const today = localDate();
      return { forecast: { ...cached, days: cached.days.filter((d) => d.date >= today) }, cached: true };
    }
    throw e;
  }
}
