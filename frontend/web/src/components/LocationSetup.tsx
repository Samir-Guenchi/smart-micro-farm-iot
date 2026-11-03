import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { FarmProfile } from "../farm/profile";

/** Asks for the farm's coordinates once: from the phone's GPS, or typed in. */
export function LocationSetup({ profile, update }: { profile: FarmProfile; update: (p: Partial<FarmProfile>) => void }) {
  const { t } = useTranslation();
  const [lat, setLat] = useState(profile.lat?.toString() ?? "");
  const [lon, setLon] = useState(profile.lon?.toString() ?? "");
  const [msg, setMsg] = useState("");

  const useGps = () => {
    if (!("geolocation" in navigator)) return setMsg(t("farm.gpsFailed"));
    setMsg(t("common.loading"));
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const round = (n: number) => Math.round(n * 1000) / 1000; // ~100 m is plenty for weather
        update({ lat: round(pos.coords.latitude), lon: round(pos.coords.longitude) });
        setMsg("");
      },
      () => setMsg(t("farm.gpsFailed")),
      { timeout: 15000 },
    );
  };

  const saveTyped = (e: React.FormEvent) => {
    e.preventDefault();
    const la = Number(lat);
    const lo = Number(lon);
    if (lat === "" || lon === "" || !Number.isFinite(la) || !Number.isFinite(lo) || Math.abs(la) > 90 || Math.abs(lo) > 180) {
      return setMsg(t("farm.badCoords"));
    }
    update({ lat: la, lon: lo });
    setMsg("");
  };

  return (
    <div className="card stack">
      <h2>{t("farm.location")}</h2>
      <p className="muted">{t("farm.locationHelp")}</p>
      <button className="primary" type="button" onClick={useGps}>
        📍 {t("farm.useGps")}
      </button>
      <form className="row" onSubmit={saveTyped}>
        <label>
          {t("farm.lat")}
          <input inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} />
        </label>
        <label>
          {t("farm.lon")}
          <input inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} />
        </label>
        <button type="submit">{t("farm.save")}</button>
      </form>
      {msg && <p role="status">{msg}</p>}
    </div>
  );
}
