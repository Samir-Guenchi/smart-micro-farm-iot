import { useTranslation } from "react-i18next";
import { api } from "../api";
import { NodeCard } from "../components/NodeCard";
import { usePolling } from "../hooks";

export function Overview() {
  const { t } = useTranslation();
  const { data, error, refresh } = usePolling(api.nodes, []);

  return (
    <section>
      <h1 className="sr-only">{t("nav.overview")}</h1>
      {error && !data ? <ErrorBox onRetry={refresh} /> : null}
      {!data && !error ? <p className="muted">{t("common.loading")}</p> : null}
      <div className="grid">{data?.map((node) => <NodeCard key={node.id} node={node} />)}</div>
    </section>
  );
}

export function ErrorBox({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="card error-box" role="alert">
      <p>{t("common.error")}</p>
      <button onClick={onRetry}>{t("common.retry")}</button>
    </div>
  );
}
