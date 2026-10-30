import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { api, setToken } from "../api";

export function Login() {
  const { t } = useTranslation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(false);
    try {
      const { token } = await api.login(username, password);
      setToken(token);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <img src="icons/icon-192.png" alt="" width={96} height={96} />
      <h1>{t("app.name")}</h1>
      <form onSubmit={submit} className="card">
        <h2>{t("login.title")}</h2>
        <label>
          {t("login.username")}
          <input autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          {t("login.password")}
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {error && <p className="error">{t("login.error")}</p>}
        <button className="primary big" disabled={busy}>
          {t("login.submit")}
        </button>
      </form>
    </main>
  );
}
