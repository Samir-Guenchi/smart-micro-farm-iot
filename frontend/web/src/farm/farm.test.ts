import { describe, expect, it } from "vitest";
import { totals, toCsv, whatsappLink, type Entry } from "./book";
import { forecastUrl, parseForecast } from "./forecast";
import { degreeDays, fungalRisk, hourly, mildewRisk, tutaStatus } from "./health";
import { planDay, weekTotals } from "./water";

describe("water plan", () => {
  const day = { date: "2027-07-01", et0: 6, rainMm: 0, tMax: 36, tMin: 22 };

  it("turns evapotranspiration into liters and drip minutes", () => {
    // Tomato in full growth: 6 mm × 1.15 = 6.9 mm; 10 m² → 69 L; /0.9 drip efficiency → 76.7 L; at 40 L/h → 115 min.
    const p = planDay(day, "tomato", "mid", 10, 40);
    expect(p.needMm).toBeCloseTo(6.9);
    expect(p.liters).toBeCloseTo(76.67, 1);
    expect(p.minutes).toBeCloseTo(115, 0);
    expect(p.hot).toBe(true);
  });

  it("counts 80 % of the rain and never goes below zero", () => {
    expect(planDay({ ...day, rainMm: 5 }, "tomato", "mid", 10, 40).netMm).toBeCloseTo(2.9);
    expect(planDay({ ...day, rainMm: 20 }, "tomato", "mid", 10, 40).liters).toBe(0);
  });

  it("young plants need less than full-grown ones", () => {
    expect(planDay(day, "tomato", "ini", 10, 40).liters).toBeLessThan(planDay(day, "tomato", "mid", 10, 40).liters);
  });

  it("totals the week and its cost", () => {
    const plan = [planDay(day, "lettuce", "mid", 9, 30), planDay(day, "lettuce", "mid", 9, 30)];
    const w = weekTotals(plan, 50);
    expect(w.liters).toBeCloseTo(120);
    expect(w.cost).toBeCloseTo(6);
  });
});

describe("forecast", () => {
  it("asks Open-Meteo for daily ET0 and past temperatures", () => {
    const url = new URL(forecastUrl(36.75, 3.06));
    expect(url.searchParams.get("daily")).toContain("et0_fao_evapotranspiration");
    expect(url.searchParams.get("past_days")).toBe("92");
  });

  it("splits past days from the forecast", () => {
    const f = parseForecast(
      {
        daily: {
          time: ["2027-06-30", "2027-07-01", "2027-07-02"],
          et0_fao_evapotranspiration: [5, 6, null],
          precipitation_sum: [0, 1.2, null],
          temperature_2m_max: [30, 33, 34],
          temperature_2m_min: [18, 19, 20],
          temperature_2m_mean: [24, 26, 27],
        },
      },
      "2027-07-01",
      1,
    );
    expect(f.days.map((d) => d.date)).toEqual(["2027-07-01", "2027-07-02"]);
    expect(f.days[1].et0).toBe(0);
    expect(f.past).toEqual([
      { date: "2027-06-30", tMean: 24 },
      { date: "2027-07-01", tMean: 26 },
    ]);
  });
});

describe("plant health", () => {
  const H = 3600;
  const now = 100 * 86400;
  const series = (n: number, f: (i: number) => number) => Array.from({ length: n }, (_, i) => ({ ts: now - (n - i) * H + 60, value: f(i) }));

  it("averages readings into hours that have both values", () => {
    const hours = hourly(
      [
        { ts: 7200, value: 10 },
        { ts: 7500, value: 14 },
        { ts: 10800, value: 20 },
      ],
      [{ ts: 7300, value: 95 }],
    );
    expect(hours).toEqual([{ hour: 7200, temp: 12, rh: 95 }]);
  });

  it("flags blight weather after a long humid night", () => {
    const wet = hourly(series(72, () => 18), series(72, (i) => (i >= 50 ? 95 : 60)));
    expect(fungalRisk(wet, now).level).toBe("high");
    const dry = hourly(series(72, () => 18), series(72, () => 60));
    expect(fungalRisk(dry, now)).toEqual({ level: "low", worstDayHours: 0 });
  });

  it("does not count humid hours that are too cold for spores", () => {
    const cold = hourly(series(72, () => 5), series(72, () => 98));
    expect(fungalRisk(cold, now).level).toBe("low");
  });

  it("rates powdery mildew by warm, half-humid hours", () => {
    const hours = hourly(series(72, () => 25), series(72, () => 60));
    expect(mildewRisk(hours, now)).toEqual({ level: "high", hours: 71 }) // the hour that started exactly 72 h ago is out;
  });

  it("counts Tuta absoluta degree-days since a date", () => {
    const days = [
      { date: "2027-05-01", tMean: 30 },
      { date: "2027-05-02", tMean: 20 },
      { date: "2027-05-03", tMean: 5 },
    ];
    expect(degreeDays(days, "2027-05-02")).toBeCloseTo(11.9);
    expect(tutaStatus(450).checkTraps).toBe(true);
    expect(tutaStatus(500)).toMatchObject({ generations: 1, checkTraps: false });
  });
});

describe("farm book", () => {
  const entries: Entry[] = [
    { id: "1", date: "2027-06-01", kind: "harvest", crop: "Tomato", kg: 50 },
    { id: "2", date: "2027-06-02", kind: "sale", crop: "Tomato", kg: 40, pricePerKg: 120, buyer: "Souk" },
    { id: "3", date: "2027-06-02", kind: "sale", crop: "Tomato", kg: 10, pricePerKg: 90 },
    { id: "4", date: "2027-05-01", kind: "cost", category: "seeds", amount: 1500, crop: "Tomato" },
    { id: "5", date: "2027-05-01", kind: "cost", category: "water", amount: 800, note: "tanker, 4 m³" },
  ];

  it("totals per crop and overall", () => {
    const t = totals(entries);
    const tomato = t.crops.find((c) => c.crop === "Tomato")!;
    expect(tomato).toMatchObject({ harvestedKg: 50, soldKg: 50, income: 5700, costs: 1500, profit: 4200, avgPrice: 114 });
    expect(t.crops.find((c) => c.crop === "")!.costs).toBe(800);
    expect(t).toMatchObject({ income: 5700, costs: 2300, profit: 3400 });
  });

  it("exports CSV sorted by date with quoted fields", () => {
    const csv = toCsv(entries).trim().split("\n");
    expect(csv[0]).toBe("date,kind,crop,kg,price_per_kg,amount,category,buyer,note");
    expect(csv[1]).toBe("2027-05-01,cost,Tomato,,,1500,seeds,,");
    expect(csv[2]).toBe('2027-05-01,cost,,,,800,water,,"tanker, 4 m³"');
    expect(csv).toHaveLength(6);
  });

  it("builds a WhatsApp link with the message", () => {
    const url = new URL(whatsappLink("Tomates 40 kg", "+213 555 12 34 56"));
    expect(url.host).toBe("wa.me");
    expect(url.pathname).toBe("/213555123456");
    expect(url.searchParams.get("text")).toBe("Tomates 40 kg");
  });
});
