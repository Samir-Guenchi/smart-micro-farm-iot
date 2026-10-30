import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";
import { LineChart } from "../components/LineChart";
import { WaterButton } from "../components/WaterButton";
import { usePolling } from "../hooks";
import { ErrorBox } from "./Overview";

const NODE = "irrigation-1";
const RANGES = [6, 24, 72];

export function Bed() {
  const { t, i18n } = useTranslation();
  const [hours, setHours] = useState(24);
  const history = usePolling(() => {
    const to = Math.floor(Date.now() / 1000);
    return api.readings(NODE, "soil_moisture_pct", to - hours * 3600, to);
  }, [hours]);
  const nodes = usePolling(api.nodes, [], 15_000);
  const node = nodes.data?.find((n) => n.id === NODE);
  const pumpOn = node?.latest.pump_on === 1;

  return (
    <section className="stack">
      <h1>{t("bed.title")}</h1>

      <div className="card">
        <header className="card-head">
          <h2>{t("bed.pump")}</h2>
          <span className={`badge ${pumpOn ? "on" : "off"}`}>{pumpOn ? t("bed.pumpOn") : t("bed.pumpOff")}</span>
        </header>
        <WaterButton node={NODE} onStarted={() => setTimeout(nodes.refresh, 1000)} />
      </div>

      <div className="card">
        <header className="card-head">
          <h2>{t("bed.history", { hours })}</h2>
          <select aria-label={t("bed.range")} value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            {RANGES.map((h) => (
              <option key={h} value={h}>
                {t("bed.hours", { count: h })}
              </option>
            ))}
          </select>
        </header>
        {history.error && !history.data ? <ErrorBox onRetry={history.refresh} /> : null}
        {!history.data && !history.error ? <p className="muted">{t("common.loading")}</p> : null}
        {history.data && history.data.length < 2 ? <p className="muted">{t("bed.noData")}</p> : null}
        {history.data ? (
          <LineChart data={history.data} min={0} max={100} unit="%" label={t("bed.history", { hours })} lang={i18n.language} />
        ) : null}
      </div>
    </section>
  );
}
