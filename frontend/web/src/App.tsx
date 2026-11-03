import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { HashRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { USE_MOCK, getToken } from "./api";
import { useOnline } from "./hooks";
import { Bed } from "./pages/Bed";
import { Book } from "./pages/Book";
import { Coop } from "./pages/Coop";
import { Health } from "./pages/Health";
import { Login } from "./pages/Login";
import { Overview } from "./pages/Overview";
import { Settings } from "./pages/Settings";
import { Tools } from "./pages/Tools";
import { Water } from "./pages/Water";

const TOOL_PATHS = ["/water", "/health", "/book"];

function useToken() {
  const [token, set] = useState(getToken());
  useEffect(() => {
    const update = () => set(getToken());
    window.addEventListener("greenloop:auth", update);
    return () => window.removeEventListener("greenloop:auth", update);
  }, []);
  return token;
}

export function App() {
  const { t } = useTranslation();
  const token = useToken();
  const online = useOnline();

  if (!token) return <Login />;

  return (
    <HashRouter>
      <header className="topbar">
        <img src="icons/favicon.svg" alt="" width={28} height={28} />
        <span>{t("app.name")}</span>
      </header>
      {!online && <div className="banner warn">{t("app.offlineBanner")}</div>}
      {USE_MOCK && <div className="banner">{t("app.demoBanner")}</div>}
      <main className="content">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/bed" element={<Bed />} />
          <Route path="/coop" element={<Coop />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/water" element={<Water />} />
          <Route path="/health" element={<Health />} />
          <Route path="/book" element={<Book />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <nav className="tabbar">
        <NavLink to="/" end>
          <span aria-hidden>🏡</span>
          {t("nav.overview")}
        </NavLink>
        <NavLink to="/bed">
          <span aria-hidden>🌱</span>
          {t("nav.bed")}
        </NavLink>
        <NavLink to="/coop">
          <span aria-hidden>🐔</span>
          {t("nav.coop")}
        </NavLink>
        <NavLink to="/tools" className={({ isActive }) => (isActive || TOOL_PATHS.includes(window.location.hash.slice(1)) ? "active" : "")}>
          <span aria-hidden>🧰</span>
          {t("nav.tools")}
        </NavLink>
        <NavLink to="/settings">
          <span aria-hidden>⚙️</span>
          {t("nav.settings")}
        </NavLink>
      </nav>
    </HashRouter>
  );
}
