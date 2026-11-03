import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { COST_CATEGORIES, type CostCategory, type Entry, newId, toCsv, totals, useBook, whatsappLink } from "../farm/book";
import { localDate } from "../farm/forecast";
import { useProfile } from "../farm/profile";
import { CROPS } from "../farm/water";

type Kind = Entry["kind"];
const KINDS: Kind[] = ["harvest", "sale", "cost"];

export function Book() {
  const { t, i18n } = useTranslation();
  const [profile] = useProfile();
  const { entries, add, remove, saved } = useBook();
  const sum = useMemo(() => totals(entries), [entries]);
  const money = (n: number) => `${new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 0 }).format(n)} ${profile.currency}`;
  const kg = (n: number) => `${new Intl.NumberFormat(i18n.language, { maximumFractionDigits: 1 }).format(n)} kg`;
  const cropNames = Object.keys(CROPS).map((c) => t(`crops.${c}`));

  const exportCsv = () => {
    const url = URL.createObjectURL(new Blob([toCsv(entries)], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `greenloop-farm-book-${localDate()}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section className="stack">
      <h1>{t("book.title")}</h1>
      <datalist id="crop-names">
        {cropNames.map((c) => (
          <option key={c} value={c} />
        ))}
      </datalist>

      <div className="card">
        <dl className="metrics" data-testid="book-totals">
          <div className="metric">
            <dt>{t("book.income")}</dt>
            <dd>{money(sum.income)}</dd>
          </div>
          <div className="metric">
            <dt>{t("book.costs")}</dt>
            <dd>{money(sum.costs)}</dd>
          </div>
          <div className="metric">
            <dt>{t("book.profit")}</dt>
            <dd className={sum.profit < 0 ? "error" : undefined}>{money(sum.profit)}</dd>
          </div>
        </dl>
        {sum.crops.some((c) => c.crop) && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("book.crop")}</th>
                  <th>{t("book.harvested")}</th>
                  <th>{t("book.sold")}</th>
                  <th>{t("book.avgPrice")}</th>
                  <th>{t("book.profit")}</th>
                </tr>
              </thead>
              <tbody>
                {sum.crops.map((c) => (
                  <tr key={c.crop}>
                    <td>{c.crop || t("book.general")}</td>
                    <td>{c.harvestedKg ? kg(c.harvestedKg) : "–"}</td>
                    <td>{c.soldKg ? kg(c.soldKg) : "–"}</td>
                    <td>{c.avgPrice !== null ? `${money(c.avgPrice)}/kg` : "–"}</td>
                    <td>{money(c.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AddEntry onAdd={add} />
      <Listing currency={profile.currency} />

      <div className="card stack">
        <header className="card-head">
          <h2>{t("book.entries")}</h2>
          <button type="button" onClick={exportCsv} disabled={!entries.length}>
            ⬇️ {t("book.export")}
          </button>
        </header>
        {!saved && <p className="error">{t("book.notSaved")}</p>}
        {!entries.length && <p className="muted">{t("book.empty")}</p>}
        <ul className="entries">
          {entries.map((e) => (
            <li key={e.id}>
              <span>
                <strong>{t(`book.kinds.${e.kind}`)}</strong> · {e.date} ·{" "}
                {e.kind === "harvest" && `${e.crop} ${kg(e.kg)}`}
                {e.kind === "sale" && `${e.crop} ${kg(e.kg)} × ${money(e.pricePerKg)} = ${money(e.kg * e.pricePerKg)}${e.buyer ? ` (${e.buyer})` : ""}`}
                {e.kind === "cost" && `${t(`book.categories.${e.category}`)}${e.crop ? ` (${e.crop})` : ""}: ${money(e.amount)}`}
                {e.note ? ` · ${e.note}` : ""}
              </span>
              <button
                type="button"
                aria-label={t("book.delete")}
                onClick={() => window.confirm(t("book.confirmDelete")) && remove(e.id)}
              >
                🗑️
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function AddEntry({ onAdd }: { onAdd: (e: Entry) => void }) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<Kind>("harvest");
  const [date, setDate] = useState(localDate());
  const [crop, setCrop] = useState("");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [buyer, setBuyer] = useState("");
  const [category, setCategory] = useState<CostCategory>("water");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");

  const submit = (ev: React.FormEvent) => {
    ev.preventDefault();
    const n = (s: string) => Number(s.replace(",", "."));
    const base = { id: newId(), date, note: note.trim() || undefined };
    let entry: Entry | null = null;
    if (kind === "harvest" && crop.trim() && n(qty) > 0) entry = { ...base, kind, crop: crop.trim(), kg: n(qty) };
    if (kind === "sale" && crop.trim() && n(qty) > 0 && n(price) >= 0 && price !== "")
      entry = { ...base, kind, crop: crop.trim(), kg: n(qty), pricePerKg: n(price), buyer: buyer.trim() || undefined };
    if (kind === "cost" && n(amount) > 0) entry = { ...base, kind, category, amount: n(amount), crop: crop.trim() || undefined };
    if (!entry) return setMsg(t("book.incomplete"));
    onAdd(entry);
    setQty("");
    setPrice("");
    setAmount("");
    setNote("");
    setBuyer("");
    setMsg(t("book.added"));
  };

  return (
    <form className="card stack" onSubmit={submit} aria-label={t("book.add")}>
      <h2>{t("book.add")}</h2>
      <fieldset className="segmented">
        <legend className="sr-only">{t("book.kind")}</legend>
        {KINDS.map((k) => (
          <label key={k} className={kind === k ? "active" : ""}>
            <input type="radio" name="kind" checked={kind === k} onChange={() => setKind(k)} />
            {t(`book.kinds.${k}`)}
          </label>
        ))}
      </fieldset>
      <div className="row">
        <label>
          {t("book.date")}
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </label>
        <label>
          {kind === "cost" ? t("book.cropOptional") : t("book.crop")}
          <input list="crop-names" value={crop} onChange={(e) => setCrop(e.target.value)} />
        </label>
      </div>
      {kind !== "cost" && (
        <div className="row">
          <label>
            {t("book.kg")}
            <input inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
          </label>
          {kind === "sale" && (
            <label>
              {t("book.pricePerKg")}
              <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
            </label>
          )}
        </div>
      )}
      {kind === "sale" && (
        <label>
          {t("book.buyer")}
          <input value={buyer} onChange={(e) => setBuyer(e.target.value)} />
        </label>
      )}
      {kind === "cost" && (
        <div className="row">
          <label>
            {t("book.category")}
            <select value={category} onChange={(e) => setCategory(e.target.value as CostCategory)}>
              {COST_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {t(`book.categories.${c}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t("book.amount")}
            <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
        </div>
      )}
      <label>
        {t("book.note")}
        <input value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <button className="primary" type="submit">
        {t("book.save")}
      </button>
      {msg && <p role="status">{msg}</p>}
    </form>
  );
}

function Listing({ currency }: { currency: string }) {
  const { t } = useTranslation();
  const [crop, setCrop] = useState("");
  const [qty, setQty] = useState("");
  const [price, setPrice] = useState("");
  const [place, setPlace] = useState("");
  const [phone, setPhone] = useState("");
  const ready = crop.trim() && qty.trim();
  const text = ready
    ? [
        t("listing.headline", { crop: crop.trim() }),
        t("listing.quantity", { kg: qty.trim() }),
        price.trim() ? t("listing.price", { price: price.trim(), currency }) : null,
        place.trim() ? t("listing.place", { place: place.trim() }) : null,
        phone.trim() ? t("listing.call", { phone: phone.trim() }) : null,
        t("listing.footer"),
      ]
        .filter(Boolean)
        .join("\n")
    : "";
  const canShare = typeof navigator !== "undefined" && "share" in navigator;

  return (
    <div className="card stack">
      <h2>{t("listing.title")}</h2>
      <p className="muted small">{t("listing.help")}</p>
      <div className="row">
        <label>
          {t("book.crop")}
          <input list="crop-names" value={crop} onChange={(e) => setCrop(e.target.value)} />
        </label>
        <label>
          {t("book.kg")}
          <input inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
        </label>
      </div>
      <div className="row">
        <label>
          {t("book.pricePerKg")}
          <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
        </label>
        <label>
          {t("listing.placeLabel")}
          <input value={place} onChange={(e) => setPlace(e.target.value)} />
        </label>
      </div>
      <label>
        {t("listing.phoneLabel")}
        <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} />
      </label>
      {text && (
        <>
          <pre className="listing" data-testid="listing-text">
            {text}
          </pre>
          <div className="row">
            <a className="button primary" href={whatsappLink(text)} target="_blank" rel="noreferrer">
              {t("listing.whatsapp")}
            </a>
            {canShare && (
              <button type="button" onClick={() => navigator.share({ text }).catch(() => undefined)}>
                {t("listing.share")}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
