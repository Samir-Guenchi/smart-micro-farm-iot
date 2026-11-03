import { useTranslation } from "react-i18next";
import { USE_MOCK } from "../api";
import { LocationSetup } from "../components/LocationSetup";
import { useProfile } from "../farm/profile";
import { useForecast } from "../farm/useForecast";
import { CROPS, type CropId, STAGES, type Stage, kc, planDay, weekTotals } from "../farm/water";

export function Water() {
  const { t, i18n } = useTranslation();
  const [profile, update] = useProfile();
  const { bed } = profile;
  const hasLocation = USE_MOCK || (profile.lat !== null && profile.lon !== null);
  const { forecast, cached, error, retry } = useForecast(profile.lat ?? 0, profile.lon ?? 0, hasLocation);
  const plan = forecast?.days.map((d) => planDay(d, bed.crop, bed.stage, bed.areaM2, bed.flowLph)) ?? [];
  const today = plan[0];
  const week = weekTotals(plan, profile.waterPricePerM3);

  const num = (n: number, digits = 0) => new Intl.NumberFormat(i18n.language, { maximumFractionDigits: digits }).format(n);
  const day = (date: string) =>
    new Intl.DateTimeFormat(i18n.language, { weekday: "short", day: "numeric" }).format(new Date(`${date}T12:00:00`));
  const setNumber = (key: "areaM2" | "flowLph") => (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = Number(e.target.value);
    if (Number.isFinite(v) && v >= 0) update({ bed: { ...bed, [key]: v } });
  };

  return (
    <section className="stack">
      <h1>{t("water.title")}</h1>

      {!hasLocation && <LocationSetup profile={profile} update={update} />}

      {today && (
        <div className="card today" data-testid="water-today">
          <p className="muted">{t("water.today")}</p>
          <p className="big-number">{t("water.liters", { liters: num(today.liters) })}</p>
          <p>{t("water.minutes", { minutes: num(today.minutes) })}</p>
          <p className="muted small">{t("water.timing")}</p>
          {today.hot && <p className="warn-text">🔥 {t("water.hotDay", { temp: num(today.tMax) })}</p>}
          {today.rainMm >= 2 && <p className="ok">🌧️ {t("water.rainDay", { mm: num(today.rainMm, 1) })}</p>}
        </div>
      )}
      {hasLocation && !forecast && !error && <p className="muted">{t("common.loading")}</p>}
      {error && !forecast && (
        <div className="card error-box" role="alert">
          <p>{t("water.forecastError")}</p>
          <button onClick={retry}>{t("common.retry")}</button>
        </div>
      )}
      {cached && forecast && (
        <p className="banner warn">{t("water.cached", { when: new Intl.DateTimeFormat(i18n.language, { dateStyle: "short", timeStyle: "short" }).format(forecast.fetchedAt) })}</p>
      )}

      {plan.length > 0 && (
        <div className="card">
          <h2>{t("water.week")}</h2>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("water.day")}</th>
                  <th>{t("water.tmax")}</th>
                  <th>{t("water.rain")}</th>
                  <th>{t("water.need")}</th>
                  <th>{t("water.drip")}</th>
                </tr>
              </thead>
              <tbody>
                {plan.map((d) => (
                  <tr key={d.date} className={d.hot ? "hot" : undefined}>
                    <td>{day(d.date)}</td>
                    <td>
                      {num(d.tMax)}°{d.hot ? " 🔥" : ""}
                    </td>
                    <td>{d.rainMm > 0 ? `${num(d.rainMm, 1)} mm` : "–"}</td>
                    <td>{num(d.liters)} L</td>
                    <td>{num(d.minutes)} min</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            {t("water.weekTotal", { liters: num(week.liters) })}
            {profile.waterPricePerM3 > 0 && ` · ${t("water.weekCost", { cost: num(week.cost), currency: profile.currency })}`}
          </p>
          <p className="muted small">{t("water.method", { kc: num(kc(bed.crop, bed.stage), 2) })}</p>
        </div>
      )}

      <div className="card stack">
        <h2>{t("water.setup", { name: t("bed.title") })}</h2>
        <label>
          {t("water.crop")}
          <select value={bed.crop} onChange={(e) => update({ bed: { ...bed, crop: e.target.value as CropId } })}>
            {Object.keys(CROPS).map((c) => (
              <option key={c} value={c}>
                {t(`crops.${c}`)}
              </option>
            ))}
          </select>
        </label>
        <fieldset className="segmented">
          <legend>{t("water.stage")}</legend>
          {STAGES.map((s: Stage) => (
            <label key={s} className={bed.stage === s ? "active" : ""}>
              <input type="radio" name="stage" checked={bed.stage === s} onChange={() => update({ bed: { ...bed, stage: s } })} />
              {t(`water.stages.${s}`)}
            </label>
          ))}
        </fieldset>
        <div className="row">
          <label>
            {t("water.area")}
            <input type="number" min={0} step="any" inputMode="decimal" value={bed.areaM2} onChange={setNumber("areaM2")} />
          </label>
          <label>
            {t("water.flow")}
            <input type="number" min={0} step="any" inputMode="decimal" value={bed.flowLph} onChange={setNumber("flowLph")} />
          </label>
        </div>
        <p className="muted small">{t("water.flowHelp")}</p>
        <div className="row">
          <label>
            {t("water.price")}
            <input
              type="number"
              min={0}
              step="any"
              inputMode="decimal"
              value={profile.waterPricePerM3 || ""}
              onChange={(e) => update({ waterPricePerM3: Math.max(0, Number(e.target.value) || 0) })}
            />
          </label>
          <label>
            {t("water.currency")}
            <input value={profile.currency} maxLength={5} onChange={(e) => update({ currency: e.target.value })} />
          </label>
        </div>
        {hasLocation && !USE_MOCK && (
          <button type="button" onClick={() => update({ lat: null, lon: null })}>
            📍 {t("farm.changeLocation")}
          </button>
        )}
      </div>
    </section>
  );
}
