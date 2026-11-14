import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type * as maplibregl from "maplibre-gl";
import { CONT } from "./config";
import { norm, type FC, type Feature } from "./geo";

export type Hit = { key: string; label: string; sub: string; go: () => void };

const COORD = /^\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$/;

/** Search state for the hero bar. Results come from `hits`; ponytail: only countries and coordinates today. Future data sources become new entries there. */
export function useSearch(data: FC | undefined, map: React.RefObject<maplibregl.Map | null>, onPickCountry: (f: Feature) => void) {
  const [q, setQ] = useState("");
  const [activeHit, setActiveHit] = useState(0);
  const [focus, setFocus] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const done = useCallback(() => { setQ(""); input.current?.blur(); }, []);

  const hits: Hit[] = useMemo(() => {
    const t = q.trim();
    if (!t) return [];
    const c = COORD.exec(t);
    if (c) {
      const lat = +c[1].replace(",", "."), lon = +c[2].replace(",", ".");
      if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return [];
      return [{ key: "xy", label: `Ir para ${lat}, ${lon}`, sub: "Coordenadas (lat, lon)", go: () => { map.current?.flyTo({ center: [lon, lat], zoom: 6, duration: 1500 }); done(); } }];
    }
    const n = norm(t);
    return (data?.features ?? [])
      .map((f) => ({ f, name: norm(String(f.properties.NAME_PT ?? f.properties.NAME)) }))
      .filter((x) => x.name.includes(n))
      .sort((a, b) => Number(b.name.startsWith(n)) - Number(a.name.startsWith(n)) || a.name.localeCompare(b.name))
      .slice(0, 6)
      .map(({ f }) => ({ key: f.properties.ADM0_A3, label: f.properties.NAME_PT ?? f.properties.NAME, sub: CONT[f.properties.CONTINENT]?.pt ?? f.properties.CONTINENT, go: () => { onPickCountry(f); done(); } }));
  }, [q, data, map, onPickCountry, done]);

  useEffect(() => setActiveHit(0), [q]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "/" && document.activeElement?.tagName !== "INPUT") { e.preventDefault(); input.current?.focus(); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActiveHit((activeHit + 1) % Math.max(1, hits.length)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActiveHit((activeHit + hits.length - 1) % Math.max(1, hits.length)); }
    else if (e.key === "Enter") hits[activeHit]?.go();
    else if (e.key === "Escape") done();
  };

  return { q, setQ, hits, activeHit, setActiveHit, focus, setFocus, input, onKey };
}
