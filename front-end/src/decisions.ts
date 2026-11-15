import { useSyncExternalStore } from "react";

/** Aceitar/ignorar recomendação (A17): localStorage por área + horizonte + unidade + regra. Sem backend com estado. */
export type Decision = { status: "accepted" | "ignored"; reason?: string; at: string; area: string; horizon: number; unit: string; unitName?: string | null; rule: string };
const KEY = "fv.decisions";
const read = (): Record<string, Decision> => { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; } };
let state = read();
const subs = new Set<() => void>();

export const decisionKey = (area: string, horizon: number, unit: string, rule: string) => `${area}|${horizon}|${unit}|${rule}`;

export function decide(d: Omit<Decision, "at"> | null, key: string) {
  const next = { ...state };
  if (d) next[key] = { ...d, at: new Date().toISOString() }; else delete next[key];
  state = next; localStorage.setItem(KEY, JSON.stringify(state)); subs.forEach((f) => f());
}

export const useDecisions = () => useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => state);
export const forArea = (all: Record<string, Decision>, area: string, horizon: number) =>
  Object.values(all).filter((d) => d.area === area && d.horizon === horizon);
