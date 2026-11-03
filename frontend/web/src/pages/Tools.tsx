import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

const TOOLS = [
  { to: "/water", icon: "💧", key: "water" },
  { to: "/health", icon: "🩺", key: "health" },
  { to: "/book", icon: "📒", key: "book" },
] as const;

export function Tools() {
  const { t } = useTranslation();
  return (
    <section className="stack">
      <h1>{t("tools.title")}</h1>
      {TOOLS.map((tool) => (
        <Link key={tool.to} to={tool.to} className="card card-link tool">
          <span aria-hidden className="tool-icon">
            {tool.icon}
          </span>
          <span>
            <strong>{t(`${tool.key}.title`)}</strong>
            <br />
            <span className="muted small">{t(`tools.${tool.key}`)}</span>
          </span>
        </Link>
      ))}
    </section>
  );
}
