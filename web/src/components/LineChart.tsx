import type { Reading } from "../api";

type Props = {
  data: Reading[];
  min?: number;
  max?: number;
  unit?: string;
  label: string;
  lang: string;
};

const W = 600;
const H = 220;
const PAD = { top: 12, right: 12, bottom: 28, left: 40 };

/** Small dependency-free SVG line chart. Time runs left to right even in RTL layouts, as on paper charts. */
export function LineChart({ data, min, max, unit = "", label, lang }: Props) {
  if (data.length < 2) return null;
  const xs = data.map((d) => d.ts);
  const ys = data.map((d) => d.value);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = min ?? Math.floor(Math.min(...ys) - 1);
  const y1 = max ?? Math.ceil(Math.max(...ys) + 1);
  const sx = (x: number) => PAD.left + ((x - x0) / (x1 - x0 || 1)) * (W - PAD.left - PAD.right);
  const sy = (y: number) => H - PAD.bottom - ((y - y0) / (y1 - y0 || 1)) * (H - PAD.top - PAD.bottom);
  const path = data.map((d, i) => `${i ? "L" : "M"}${sx(d.ts).toFixed(1)},${sy(d.value).toFixed(1)}`).join(" ");
  const area = `${path} L${sx(x1).toFixed(1)},${sy(y0)} L${sx(x0).toFixed(1)},${sy(y0)} Z`;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => y0 + f * (y1 - y0));
  const xTicks = [0, 1 / 3, 2 / 3, 1].map((f) => x0 + f * (x1 - x0));
  const fmtTime = new Intl.DateTimeFormat(lang, { hour: "2-digit", minute: "2-digit" });
  const last = data[data.length - 1];

  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label} style={{ direction: "ltr" }}>
      {yTicks.map((y) => (
        <g key={y}>
          <line className="chart-grid" x1={PAD.left} x2={W - PAD.right} y1={sy(y)} y2={sy(y)} />
          <text className="chart-tick" x={PAD.left - 6} y={sy(y) + 4} textAnchor="end">
            {Math.round(y)}
            {unit}
          </text>
        </g>
      ))}
      {xTicks.map((x, i) => (
        <text key={x} className="chart-tick" x={sx(x)} y={H - 8} textAnchor={i === 0 ? "start" : i === xTicks.length - 1 ? "end" : "middle"}>
          {fmtTime.format(new Date(x * 1000))}
        </text>
      ))}
      <path className="chart-area" d={area} />
      <path className="chart-line" d={path} />
      <circle className="chart-dot" cx={sx(last.ts)} cy={sy(last.value)} r={4} />
    </svg>
  );
}
