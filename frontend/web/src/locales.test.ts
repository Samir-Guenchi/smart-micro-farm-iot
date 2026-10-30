import { describe, expect, it } from "vitest";
import ar from "./locales/ar.json";
import en from "./locales/en.json";
import fr from "./locales/fr.json";
import i18n from "./i18n";

// Base keys with plural suffixes removed, so "minutes_one" and "minutes_few" both count as "minutes".
function keys(obj: object, prefix = ""): Set<string> {
  const out = new Set<string>();
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix + k;
    if (v && typeof v === "object") keys(v, path + ".").forEach((x) => out.add(x));
    else out.add(path.replace(/_(zero|one|two|few|many|other)$/, ""));
  }
  return out;
}

function placeholders(obj: object, prefix = "", out: Record<string, string[]> = {}) {
  for (const [k, v] of Object.entries(obj)) {
    if (v && typeof v === "object") placeholders(v, prefix + k + ".", out);
    else out[prefix + k] = [...String(v).matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
  }
  return out;
}

describe("translations", () => {
  it.each([["fr", fr], ["ar", ar]])("%s has every English key", (_, locale) => {
    expect([...keys(locale)].sort()).toEqual([...keys(en)].sort());
  });

  it.each([["fr", fr], ["ar", ar]])("%s keeps the placeholders of each key", (_, locale) => {
    const enP = placeholders(en);
    for (const [key, names] of Object.entries(placeholders(locale))) {
      const base = key.replace(/_(zero|one|two|few|many|other)$/, "");
      const enKey = Object.keys(enP).find((k) => k === key || k.replace(/_(zero|one|two|few|many|other)$/, "") === base);
      expect(enKey, key).toBeDefined();
      // A plural form may drop {{count}} ("منذ دقيقة"), but must not invent new placeholders.
      for (const n of names) expect(enP[enKey!], key).toContain(n);
    }
  });

  it("uses Arabic plural forms", async () => {
    await i18n.changeLanguage("ar");
    expect(i18n.t("common.minutesAgo", { count: 2 })).toBe("منذ دقيقتين");
    expect(i18n.t("common.minutesAgo", { count: 5 })).toBe("منذ 5 دقائق");
    expect(i18n.t("common.minutesAgo", { count: 11 })).toBe("منذ 11 دقيقة");
    await i18n.changeLanguage("fr");
    expect(i18n.t("bed.minutes", { count: 10 })).toBe("10 minutes");
    await i18n.changeLanguage("en");
  });
});
