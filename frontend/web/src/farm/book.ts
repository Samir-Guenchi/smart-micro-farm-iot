// Farm book: harvests, sales and costs, kept on this device (works offline), exportable as CSV.
import { useCallback, useState } from "react";
import { loadList, save } from "./storage";

export type Entry =
  | { id: string; date: string; kind: "harvest"; crop: string; kg: number; note?: string }
  | { id: string; date: string; kind: "sale"; crop: string; kg: number; pricePerKg: number; buyer?: string; note?: string }
  | { id: string; date: string; kind: "cost"; category: CostCategory; amount: number; crop?: string; note?: string };

export const COST_CATEGORIES = ["water", "seeds", "fertilizer", "treatment", "fuel", "labor", "other"] as const;
export type CostCategory = (typeof COST_CATEGORIES)[number];

const KEY = "greenloop.book";

export function newId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export type CropTotals = { crop: string; harvestedKg: number; soldKg: number; income: number; costs: number; avgPrice: number | null; profit: number };

/** Totals per crop, plus a row with crop "" for costs not tied to a crop. Sorted by income. */
export function totals(entries: Entry[]): { crops: CropTotals[]; income: number; costs: number; profit: number } {
  const by = new Map<string, CropTotals>();
  const row = (crop: string) => {
    let r = by.get(crop);
    if (!r) by.set(crop, (r = { crop, harvestedKg: 0, soldKg: 0, income: 0, costs: 0, avgPrice: null, profit: 0 }));
    return r;
  };
  for (const e of entries) {
    if (e.kind === "harvest") row(e.crop).harvestedKg += e.kg;
    else if (e.kind === "sale") {
      const r = row(e.crop);
      r.soldKg += e.kg;
      r.income += e.kg * e.pricePerKg;
    } else row(e.crop ?? "").costs += e.amount;
  }
  const crops = [...by.values()].map((r) => ({ ...r, avgPrice: r.soldKg > 0 ? r.income / r.soldKg : null, profit: r.income - r.costs }));
  crops.sort((a, b) => b.income - a.income || a.crop.localeCompare(b.crop));
  const income = crops.reduce((s, r) => s + r.income, 0);
  const costs = crops.reduce((s, r) => s + r.costs, 0);
  return { crops, income, costs, profit: income - costs };
}

function csvCell(v: unknown) {
  const s = v === undefined || v === null ? "" : String(v);
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(entries: Entry[]): string {
  const head = ["date", "kind", "crop", "kg", "price_per_kg", "amount", "category", "buyer", "note"];
  const rows = [...entries]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((e) => {
      const amount = e.kind === "sale" ? e.kg * e.pricePerKg : e.kind === "cost" ? e.amount : "";
      return [
        e.date,
        e.kind,
        e.kind === "cost" ? (e.crop ?? "") : e.crop,
        e.kind === "cost" ? "" : e.kg,
        e.kind === "sale" ? e.pricePerKg : "",
        amount,
        e.kind === "cost" ? e.category : "",
        e.kind === "sale" ? (e.buyer ?? "") : "",
        e.note ?? "",
      ].map(csvCell);
    });
  return [head, ...rows].map((r) => r.join(",")).join("\n") + "\n";
}

export function whatsappLink(text: string, phone = "") {
  const digits = phone.replace(/\D/g, "");
  return `https://wa.me/${digits}?text=${encodeURIComponent(text)}`;
}

export function useBook() {
  const [entries, setEntries] = useState<Entry[]>(() => loadList<Entry>(KEY));
  const [saved, setSaved] = useState(true);
  const write = useCallback((f: (prev: Entry[]) => Entry[]) => {
    setEntries((prev) => {
      const next = f(prev);
      setSaved(save(KEY, next));
      return next;
    });
  }, []);
  const add = useCallback((e: Entry) => write((prev) => [e, ...prev]), [write]);
  const remove = useCallback((id: string) => write((prev) => prev.filter((e) => e.id !== id)), [write]);
  return { entries, add, remove, saved };
}
