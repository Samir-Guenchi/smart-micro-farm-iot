import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { setToken } from "../api";
import { LANGUAGES } from "../i18n";
import { enablePush, pushState, type PushState } from "../push";

type InstallPrompt = Event & { prompt: () => Promise<void> };

export function Settings() {
  const { t, i18n } = useTranslation();
  const [push, setPush] = useState<PushState>("default");
  const [install, setInstall] = useState<InstallPrompt | null>(null);

  useEffect(() => {
    pushState().then(setPush);
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setInstall(e as InstallPrompt);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  return (
    <section className="stack">
      <h1>{t("settings.title")}</h1>

      <div className="card">
        <label>
          {t("settings.language")}
          <select value={i18n.language} onChange={(e) => i18n.changeLanguage(e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="card">
        <h2>{t("settings.notifications")}</h2>
        <p className="muted">{t("settings.notificationsHelp")}</p>
        {push === "default" && (
          <button className="primary" onClick={async () => setPush(await enablePush())}>
            {t("settings.enable")}
          </button>
        )}
        {push !== "default" && <p role="status">{t(`settings.${push}`)}</p>}
      </div>

      {install && (
        <div className="card">
          <h2>{t("settings.install")}</h2>
          <p className="muted">{t("settings.installHelp")}</p>
          <button className="primary" onClick={() => install.prompt().then(() => setInstall(null))}>
            {t("settings.install")}
          </button>
        </div>
      )}

      <button onClick={() => setToken(null)}>{t("settings.logout")}</button>
    </section>
  );
}
