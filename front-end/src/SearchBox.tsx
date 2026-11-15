import { useEffect, useRef, useState } from "react";
import { fvApi } from "./api/client";
import type { AreaHit, AreaRef } from "./api/dto";
import { t } from "./i18n";

const COORD = /^\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$/;
type Hit = { key: string; label: string; sub: string; go: () => void };

/** Busca única (RF-UI-01): país, estado, município ou coordenada. Mostra o breadcrumb quando vazia. Atalho: "/" ou ⌘K. */
export default function SearchBox({ lineage, onArea, onCoord }: { lineage: AreaRef[]; onArea: (id: string) => void; onCoord: (lat: number, lon: number) => void }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const done = () => { setQ(""); setOpen(false); input.current?.blur(); };

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.key === "/" && document.activeElement?.tagName !== "INPUT") || (e.key === "k" && (e.metaKey || e.ctrlKey))) { e.preventDefault(); input.current?.focus(); }
    };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k);
  }, []);

  useEffect(() => {
    setActive(0);
    const c = COORD.exec(q);
    if (c) {
      const lat = +c[1].replace(",", "."), lon = +c[2].replace(",", ".");
      setHits(Math.abs(lat) <= 90 && Math.abs(lon) <= 180 ? [{ key: "xy", label: t("search.coord", { lat, lon }), sub: "lat, lon", go: () => { onCoord(lat, lon); done(); } }] : []);
      return;
    }
    if (!q.trim()) { setHits([]); return; }
    const ab = new AbortController();
    const id = setTimeout(() => fvApi.areas(q, ab.signal).then((r) => setHits(r.areas.map((a: AreaHit) => ({
      key: a.area_id, label: a.name, sub: t(`level.${a.level}`), go: () => { onArea(a.area_id); done(); } })))).catch(() => undefined), 150);
    return () => { clearTimeout(id); ab.abort(); };
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((active + 1) % Math.max(1, hits.length)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((active + hits.length - 1) % Math.max(1, hits.length)); }
    else if (e.key === "Enter") hits[active]?.go();
    else if (e.key === "Escape") done();
  };

  return (
    <div className="search">
      <div className="crumbs">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        {!open && !q && lineage.length > 0 ? (
          <span className="bc" onClick={() => input.current?.focus()}>
            {lineage.map((a) => <span key={a.id}><button onClick={(e) => { e.stopPropagation(); onArea(a.id); }}>{a.name.replace(/ - [A-Z]{2}$/, "")}</button></span>)}
          </span>
        ) : null}
        <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onKeyDown={onKey} onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)} placeholder={open || !lineage.length ? t("search.placeholder") : ""}
          role="combobox" aria-expanded={open && hits.length > 0} aria-controls="fv-hits" aria-autocomplete="list" aria-label={t("search.label")}
          aria-activedescendant={open && hits[active] ? `fv-hit-${active}` : undefined} style={!open && !q && lineage.length ? { width: 8 } : undefined} />
        <kbd style={{ font: "500 10.5px var(--mono)", border: "1px solid var(--line)", borderRadius: 4, padding: "1px 5px" }}>⌘K</kbd>
      </div>
      {open && q.trim() && (
        <ul id="fv-hits" role="listbox" className="hits">
          {hits.length ? hits.map((h, i) => (
            <li key={h.key} id={`fv-hit-${i}`} role="option" aria-selected={i === active} onMouseDown={(e) => e.preventDefault()} onClick={() => h.go()} onMouseEnter={() => setActive(i)}>
              <b>{h.label}</b><small>{h.sub}</small></li>)) : <li>{t("search.none")}</li>}
        </ul>)}
    </div>
  );
}
