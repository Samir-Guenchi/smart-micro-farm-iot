// Crop water need from reference evapotranspiration (FAO-56): ETc = ET0 × Kc.
// 1 mm of water on 1 m² is 1 liter.

// FAO-56 Table 12 single crop coefficients (initial, mid-season, late season), rounded.
export const CROPS = {
  tomato: { ini: 0.6, mid: 1.15, end: 0.8 },
  pepper: { ini: 0.6, mid: 1.05, end: 0.9 },
  potato: { ini: 0.5, mid: 1.15, end: 0.75 },
  onion: { ini: 0.7, mid: 1.05, end: 0.75 },
  lettuce: { ini: 0.7, mid: 1.0, end: 0.95 },
  cucumber: { ini: 0.6, mid: 1.0, end: 0.75 },
  zucchini: { ini: 0.5, mid: 0.95, end: 0.75 },
  melon: { ini: 0.5, mid: 1.05, end: 0.75 },
  watermelon: { ini: 0.4, mid: 1.0, end: 0.75 },
  bean: { ini: 0.5, mid: 1.05, end: 0.9 },
  strawberry: { ini: 0.4, mid: 0.85, end: 0.75 },
  olive: { ini: 0.65, mid: 0.7, end: 0.7 },
  date_palm: { ini: 0.9, mid: 0.95, end: 0.95 },
} as const;

export type CropId = keyof typeof CROPS;
export type Stage = "ini" | "mid" | "end";
export const STAGES: Stage[] = ["ini", "mid", "end"];

export const DRIP_EFFICIENCY = 0.9; // share of the water that reaches the roots
export const EFFECTIVE_RAIN = 0.8; // share of the rain the soil keeps
export const HOT_DAY_C = 35;

export type DayWeather = { date: string; et0: number; rainMm: number; tMax: number; tMin: number };

export type DayPlan = DayWeather & {
  needMm: number; // what the crop uses, ET0 × Kc
  netMm: number; // minus effective rain, never below 0
  liters: number; // to apply with the drip, after losses
  minutes: number; // pump run time at the bed's drip flow
  hot: boolean;
};

export function kc(crop: CropId, stage: Stage): number {
  return CROPS[crop][stage];
}

export function planDay(day: DayWeather, crop: CropId, stage: Stage, areaM2: number, flowLph: number): DayPlan {
  const needMm = day.et0 * kc(crop, stage);
  const netMm = Math.max(0, needMm - EFFECTIVE_RAIN * day.rainMm);
  const liters = (netMm * areaM2) / DRIP_EFFICIENCY;
  const minutes = flowLph > 0 ? (liters / flowLph) * 60 : 0;
  return { ...day, needMm, netMm, liters, minutes, hot: day.tMax >= HOT_DAY_C };
}

export function weekTotals(plan: DayPlan[], pricePerM3: number) {
  const liters = plan.reduce((s, d) => s + d.liters, 0);
  return { liters, cost: (liters / 1000) * pricePerM3 };
}
