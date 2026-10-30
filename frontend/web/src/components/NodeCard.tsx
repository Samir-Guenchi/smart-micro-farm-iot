import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import type { NodeInfo } from "../api";
import { formatMetric, timeAgo } from "../format";

const LINKS: Record<string, string> = { "irrigation-1": "/bed", "coop-1": "/coop" };
// Most useful values first; battery last.
const ORDER = ["soil_moisture_pct", "pump_on", "hive_weight_kg", "hive_temp_c", "air_temp_c", "air_humidity_pct", "water_liters", "battery_v"];

export function NodeCard({ node }: { node: NodeInfo }) {
  const { t, i18n } = useTranslation();
  const metrics = Object.entries(node.latest).sort(([a], [b]) => ORDER.indexOf(a) - ORDER.indexOf(b));
  const body = (
    <>
      <header className="card-head">
        <h2>{t(`nodes.${node.id}`, { defaultValue: node.id })}</h2>
        <span className={`badge ${node.status}`}>{t(`common.${node.status}`)}</span>
      </header>
      <dl className="metrics">
        {metrics.map(([metric, value]) => (
          <div key={metric} className="metric">
            <dt>{t(`metrics.${metric}`, { defaultValue: metric })}</dt>
            <dd>{formatMetric(metric, value, t, i18n.language)}</dd>
          </div>
        ))}
      </dl>
      <p className="muted small">{t("common.lastSeen", { when: timeAgo(node.last_seen, t) })}</p>
    </>
  );
  const to = LINKS[node.id];
  return to ? (
    <Link to={to} className="card card-link" data-testid={`node-${node.id}`}>
      {body}
    </Link>
  ) : (
    <article className="card" data-testid={`node-${node.id}`}>
      {body}
    </article>
  );
}
