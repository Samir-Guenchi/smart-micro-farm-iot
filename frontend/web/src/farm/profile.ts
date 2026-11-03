// The farm's location and bed setup, kept on this device. Used by the water plan and plant health.
import { useCallback, useState } from "react";
import type { CropId, Stage } from "./water";
import { load, save } from "./storage";

export type Bed = {
  name: string;
  crop: CropId;
  stage: Stage;
  areaM2: number;
  flowLph: number; // drip flow of the whole bed, liters per hour
};

export type FarmProfile = {
  lat: number | null;
  lon: number | null;
  bed: Bed;
  waterPricePerM3: number; // 0 = not set
  currency: string;
  tutaSince: string; // YYYY-MM-DD, start of degree-day counting (planting or last trap reset)
};

const KEY = "greenloop.farm";

function envNumber(v: string | undefined): number | null {
  const n = v === undefined || v === "" ? NaN : Number(v);
  return Number.isFinite(n) ? n : null;
}

function daysAgo(n: number) {
  const d = new Date(Date.now() - n * 86400_000);
  return d.toISOString().slice(0, 10);
}

export function defaultProfile(): FarmProfile {
  return {
    lat: envNumber(import.meta.env.VITE_FARM_LAT),
    lon: envNumber(import.meta.env.VITE_FARM_LON),
    bed: { name: "Bed 1", crop: "tomato", stage: "mid", areaM2: 10, flowLph: 40 },
    waterPricePerM3: 0,
    currency: import.meta.env.VITE_CURRENCY || "DA",
    tutaSince: daysAgo(30),
  };
}

export function loadProfile(): FarmProfile {
  const base = defaultProfile();
  const p = load<FarmProfile>(KEY, base);
  return { ...p, bed: { ...base.bed, ...p.bed } };
}

export function useProfile() {
  const [profile, setProfile] = useState(loadProfile);
  const update = useCallback((patch: Partial<FarmProfile>) => {
    setProfile((p) => {
      const next = { ...p, ...patch, bed: { ...p.bed, ...(patch.bed ?? {}) } };
      save(KEY, next);
      return next;
    });
  }, []);
  return [profile, update] as const;
}
