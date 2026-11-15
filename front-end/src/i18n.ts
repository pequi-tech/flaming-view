import { useSyncExternalStore } from "react";
import en from "./i18n/en.json";
import pt from "./i18n/pt-BR.json";

export type Lang = "pt-BR" | "en";
const DICTS: Record<Lang, Record<string, string>> = { en, "pt-BR": pt };
const stored = localStorage.getItem("fv.lang") as Lang | null;
let lang: Lang = stored === "en" || stored === "pt-BR" ? stored : navigator.language.toLowerCase().startsWith("pt") ? "pt-BR" : "en";
const subs = new Set<() => void>();
document.documentElement.lang = lang;

export function setLang(next: Lang) {
  lang = next; localStorage.setItem("fv.lang", next); document.documentElement.lang = next;
  subs.forEach((f) => f());
}
export const getLang = () => lang;
export const useLang = () => useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => lang);

/** t("chip.metric", { auc: "0,71" }) -> texto do dicionário com {variáveis}; cai para EN e depois para a própria chave. */
export function t(key: string, vars: Record<string, string | number> = {}) {
  const s = DICTS[lang][key] ?? DICTS.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

export const num = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : v.toLocaleString(lang, { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const pct = (v: number | null | undefined, digits = 0) => (v === null || v === undefined ? "—" : `${num(v * 100, digits)} %`);
export const monthName = (ym: string | null | undefined, style: "long" | "short" = "long") => {
  if (!ym) return "—";
  const [y, m] = ym.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 15)).toLocaleDateString(lang, { month: style, year: "numeric", timeZone: "UTC" });
};
export const monthShort = (m: number) => new Date(Date.UTC(2020, m - 1, 15)).toLocaleDateString(lang, { month: "short", timeZone: "UTC" });
