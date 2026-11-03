import { useTranslation } from "react-i18next";
import { USE_MOCK, api } from "../api";
import { LocationSetup } from "../components/LocationSetup";
import { degreeDays, fungalRisk, hourly, type Level, mildewRisk, tutaStatus } from "../farm/health";
import { useProfile } from "../farm/profile";
import { useForecast } from "../farm/useForecast";
import { usePolling } from "../hooks";

const NODE = "irrigation-1";

function LevelBadge({ level }: { level: Level }) {
  const { t } = useTranslation();
  return <span className={`badge level-${level}`}>{t(`health.level.${level}`)}</span>;
}

export function Health() {
  const { t, i18n } = useTranslation();
  const [profile, update] = useProfile();
  const climate = usePolling(
    async () => {
      const to = Math.floor(Date.now() / 1000);
      const from = to - 3 * 86400;
      const [temps, hums] = await Promise.all([
        api.readings(NODE, "air_temp_c", from, to),
        api.readings(NODE, "air_humidity_pct", from, to),
      ]);
      return { hours: hourly(temps, hums), now: to };
    },
    [],
    10 * 60_000,
  );
  const hasLocation = USE_MOCK || (profile.lat !== null && profile.lon !== null);
  const { forecast } = useForecast(profile.lat ?? 0, profile.lon ?? 0, hasLocation);

  const hours = climate.data?.hours ?? [];
  const enough = hours.length >= 24;
  const fungal = climate.data ? fungalRisk(hours, climate.data.now) : null;
  const mildew = climate.data ? mildewRisk(hours, climate.data.now) : null;
  const tuta = forecast ? tutaStatus(degreeDays(forecast.past, profile.tutaSince)) : null;
  const num = (n: number) => new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 0 }).format(n);

  return (
    <section className="stack">
      <h1>{t("health.title")}</h1>
      <p className="muted small">{t("health.disclaimer")}</p>

      {!climate.data && !climate.error && <p className="muted">{t("common.loading")}</p>}
      {climate.data && !enough && <p className="muted">{t("health.noSensor")}</p>}

      {fungal && enough && (
        <div className="card" data-testid="risk-fungal">
          <header className="card-head">
            <h2>{t("health.fungal")}</h2>
            <LevelBadge level={fungal.level} />
          </header>
          <p>{t("health.fungalWhy", { count: fungal.worstDayHours })}</p>
          <p className="muted small">{t(`health.fungalAdvice.${fungal.level}`)}</p>
        </div>
      )}

      {mildew && enough && (
        <div className="card" data-testid="risk-mildew">
          <header className="card-head">
            <h2>{t("health.mildew")}</h2>
            <LevelBadge level={mildew.level} />
          </header>
          <p>{t("health.mildewWhy", { count: mildew.hours })}</p>
          <p className="muted small">{t(`health.mildewAdvice.${mildew.level}`)}</p>
        </div>
      )}

      <div className="card stack" data-testid="risk-tuta">
        <header className="card-head">
          <h2>{t("health.tuta")}</h2>
          {tuta && <LevelBadge level={tuta.checkTraps ? "high" : tuta.progress > 0.6 ? "medium" : "low"} />}
        </header>
        <label>
          {t("health.tutaSince")}
          <input type="date" value={profile.tutaSince} onChange={(e) => e.target.value && update({ tutaSince: e.target.value })} />
        </label>
        {!hasLocation && <LocationSetup profile={profile} update={update} />}
        {tuta && (
          <>
            <p>{t("health.tutaDD", { dd: num(tuta.dd) })}</p>
            <progress max={1} value={tuta.progress} aria-label={t("health.tutaProgress")} />
            <p className="muted small">{tuta.checkTraps ? t("health.tutaCheck") : t("health.tutaWait")}</p>
          </>
        )}
      </div>
    </section>
  );
}
