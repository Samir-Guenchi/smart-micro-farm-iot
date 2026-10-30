import { useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../api";

const DURATIONS_MIN = [5, 10, 15];

export function WaterButton({ node, onStarted }: { node: string; onStarted?: () => void }) {
  const { t } = useTranslation();
  const [minutes, setMinutes] = useState(10);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  async function water() {
    if (!window.confirm(t("bed.confirm", { minutes }))) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await api.pump(node, minutes * 60);
      const ran = Math.round((res.duration_s ?? minutes * 60) / 60);
      const text = t("bed.sent", { minutes: ran }) + (ran < minutes ? ` ${t("bed.capped", { minutes: ran })}` : "");
      setMessage({ kind: "ok", text });
      onStarted?.();
    } catch {
      setMessage({ kind: "error", text: t("bed.failed") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="water">
      <fieldset className="segmented">
        <legend>{t("bed.duration")}</legend>
        {DURATIONS_MIN.map((m) => (
          <label key={m} className={m === minutes ? "active" : ""}>
            <input type="radio" name="duration" value={m} checked={m === minutes} onChange={() => setMinutes(m)} />
            {t("bed.minutes", { count: m })}
          </label>
        ))}
      </fieldset>
      <button className="primary big" onClick={water} disabled={busy}>
        💧 {t("bed.water")}
      </button>
      {message && (
        <p role="status" className={message.kind}>
          {message.text}
        </p>
      )}
    </div>
  );
}
