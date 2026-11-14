import type { useSearch } from "./useSearch";

export default function SearchBar({ s }: { s: ReturnType<typeof useSearch> }) {
  const { q, setQ, hits, activeHit, setActiveHit, focus, setFocus, input, onKey } = s;
  return (
    <div className="gx-hero">
      <span className="gx-logo" aria-hidden>◐</span>
      <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey} onFocus={() => setFocus(true)} onBlur={() => setTimeout(() => setFocus(false), 120)}
        placeholder="Pesquisar países ou coordenadas (ex.: -15.8, -47.9)" role="combobox" aria-expanded={focus && hits.length > 0} aria-controls="gx-hits" aria-autocomplete="list"
        aria-activedescendant={focus && hits[activeHit] ? `gx-hit-${activeHit}` : undefined} aria-label="Pesquisar" />
      <kbd aria-hidden>/</kbd>
      {focus && q.trim() && (
        <ul id="gx-hits" role="listbox" className="gx-hits">
          {hits.length ? hits.map((h, i) => (
            <li key={h.key} id={`gx-hit-${i}`} role="option" aria-selected={i === activeHit} className={i === activeHit ? "on" : ""} onMouseDown={(e) => { e.preventDefault(); h.go(); }} onMouseEnter={() => setActiveHit(i)}>
              <b>{h.label}</b><small>{h.sub}</small></li>)) : <li className="none">Nada encontrado</li>}
        </ul>)}
    </div>
  );
}
