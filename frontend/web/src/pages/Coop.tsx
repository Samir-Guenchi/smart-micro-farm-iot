import { useTranslation } from "react-i18next";
import { api } from "../api";
import { clockTime } from "../format";
import { usePolling } from "../hooks";
import { ErrorBox } from "./Overview";

export function Coop() {
  const { t, i18n } = useTranslation();
  const { data, error, refresh } = usePolling(() => api.events({ node: "coop-1", type: "door", limit: 20 }), []);
  const latest = data?.[0];
  const state = latest?.state === "open" || latest?.state === "closed" ? latest.state : "unknown";
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  const today = (data ?? []).filter((e) => e.ts >= midnight.getTime() / 1000).reverse();

  return (
    <section className="stack">
      <h1>{t("coop.title")}</h1>
      {error && !data ? <ErrorBox onRetry={refresh} /> : null}
      <div className="card">
        <header className="card-head">
          <h2>{t("coop.door")}</h2>
        </header>
        <p className={`door door-${state}`} data-testid="door-state">
          {state === "closed" ? "🔒" : state === "open" ? "🔓" : "❔"} {t(`coop.${state}`)}
          {latest ? <span className="muted small"> {t("coop.since", { time: clockTime(latest.ts, i18n.language) })}</span> : null}
        </p>
      </div>
      <div className="card">
        <header className="card-head">
          <h2>{t("coop.today")}</h2>
        </header>
        {data && today.length === 0 ? <p className="muted">{t("coop.noEventsToday")}</p> : null}
        <ul className="timeline">
          {today.map((e, i) => (
            <li key={`${e.ts}-${i}`}>
              {e.state === "open"
                ? t("coop.openedAt", { time: clockTime(e.ts, i18n.language) })
                : t("coop.closedAt", { time: clockTime(e.ts, i18n.language) })}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
