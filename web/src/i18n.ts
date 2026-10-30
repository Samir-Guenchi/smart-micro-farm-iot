import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";

// Adding a language = adding a locale file here. Right-to-left is handled by `dir`.
export const LANGUAGES = [
  { code: "en", name: "English", dir: "ltr" },
  { code: "fr", name: "Français", dir: "ltr" },
  { code: "ar", name: "العربية", dir: "rtl" },
] as const;

const STORAGE_KEY = "greenloop.lang";

function initialLanguage(): string {
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  let saved: string | null = null;
  try {
    saved = localStorage.getItem(STORAGE_KEY);
  } catch {
    // storage blocked: fall through to the browser language
  }
  const candidate = fromUrl || saved || navigator.language.slice(0, 2);
  return LANGUAGES.some((l) => l.code === candidate) ? candidate : "en";
}

export function applyDirection(lng: string) {
  const lang = LANGUAGES.find((l) => l.code === lng) ?? LANGUAGES[0];
  document.documentElement.lang = lang.code;
  document.documentElement.dir = lang.dir;
}

i18n.on("languageChanged", (lng) => {
  applyDirection(lng);
  try {
    localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    // ignore
  }
});

i18n.use(initReactI18next).init({
  // Only English ships for now; fr and ar fall back to it until translated (issue #26).
  resources: { en: { translation: en } },
  lng: initialLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});
applyDirection(i18n.language);

export default i18n;
