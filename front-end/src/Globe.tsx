import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";

maplibregl.setWorkerUrl(workerUrl);

type FC = { type: "FeatureCollection"; features: { type: "Feature"; properties: any; geometry: any }[] };
type Country = { NAME_PT: string; NAME: string; CONTINENT: string; POP_EST: number; TYPE: string; ADM0_A3: string };

const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const fireDate = new Date(Date.now() - 3 * 864e5).toISOString().slice(0, 10);
const CONT: Record<string, { c: string; pt: string; view: [number, number, number] }> = {
  Africa: { c: "#22d3ee", pt: "África", view: [18, 2, 2.6] },
  Europe: { c: "#f472b6", pt: "Europa", view: [15, 52, 3.2] },
  Asia: { c: "#facc15", pt: "Ásia", view: [90, 35, 2.4] },
  "North America": { c: "#fb923c", pt: "América do Norte", view: [-100, 45, 2.4] },
  "South America": { c: "#fb923c", pt: "América do Sul", view: [-60, -18, 2.6] },
  Oceania: { c: "#a855f7", pt: "Oceania", view: [150, -25, 2.8] },
};
const ORDER = ["Africa", "Europe", "Asia", "North America", "South America", "Oceania"];
const contColor: any = ["match", ["get", "CONTINENT"], ...ORDER.flatMap((k) => [k, CONT[k].c]), "#8b97a8"];

const raster = (id: string, tiles: string, maxzoom: number, attribution = "NASA GIBS") =>
  ({ id, source: { type: "raster" as const, tiles: [tiles], tileSize: 256, maxzoom, attribution } });

const bboxOf = (coords: any, b = [180, 90, -180, -90]): number[] => {
  if (typeof coords[0] === "number") return [Math.min(b[0], coords[0]), Math.min(b[1], coords[1]), Math.max(b[2], coords[0]), Math.max(b[3], coords[1])];
  return coords.reduce((acc: number[], c: any) => bboxOf(c, acc), b);
};
const bigPoly = (g: any) => (g.type === "Polygon" ? g.coordinates : g.coordinates.reduce((a: any, p: any) => (bboxArea(p) > bboxArea(a) ? p : a)));
const bboxArea = (p: any) => { const b = bboxOf(p); return (b[2] - b[0]) * (b[3] - b[1]); };

const norm = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const COORD = /^\s*(-?\d+(?:[.,]\d+)?)\s*[,; ]\s*(-?\d+(?:[.,]\d+)?)\s*$/;
type Hit = { key: string; label: string; sub: string; go: () => void };

const nf = (v: number) => (v >= 1e9 ? `${(v / 1e9).toFixed(2).replace(".", ",")} bi` : v >= 1e6 ? `${(v / 1e6).toFixed(1).replace(".", ",")} mi` : v.toLocaleString("pt-BR"));

const LAYERS = [
  ["sat", "Imagem de satélite"], ["day", "Imagem diária (cor real)"], ["night", "Luzes noturnas"],
  ["fire", "Focos de calor (NOAA-20)"], ["bnd", "Fronteiras políticas"], ["lab", "Rótulos (países)"], ["pop", "População (coroplético)"],
] as const;
type LayerKey = (typeof LAYERS)[number][0];

export default function Globe() {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const coord = useRef<HTMLSpanElement>(null);
  const [data, setData] = useState<FC>();
  const [on, setOn] = useState<Record<LayerKey, boolean>>({ sat: true, day: false, night: false, fire: true, bnd: true, lab: true, pop: false });
  const [region, setRegion] = useState("World");
  const [sel, setSel] = useState<{ p: Country; bbox: number[] }>();
  const [pitch3d, setPitch3d] = useState(false);
  const [open, setOpen] = useState({ layers: true, reg: true });
  const [ready, setReady] = useState(false);
  const [q, setQ] = useState("");
  const [hi, setHi] = useState(0);
  const [focus, setFocus] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => { fetch("/data/countries.geojson").then((r) => r.json()).then(setData); }, []);

  useEffect(() => {
    if (!data) return;
    const m = new maplibregl.Map({
      container: el.current!, center: [-52, -14], zoom: 2.3, attributionControl: { compact: true }, maxPitch: 70,
      style: { version: 8, glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf", sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#02060d" } }],
        sky: { "atmosphere-blend": 0.9, "sky-color": "#0b2a5b", "horizon-color": "#3b82f6", "sky-horizon-blend": 0.6, "horizon-fog-blend": 0.4, "fog-color": "#02060d", "fog-ground-blend": 0.1 } as any },
    });
    map.current = m;
    m.on("error", (e) => { const s = String(e.error?.message ?? ""); if (!/404|400|Failed to fetch|AJAXError/.test(s)) console.error("maplibre:", s); });
    m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.on("load", () => {
      m.setProjection({ type: "globe" });
      const add = (id: string, tiles: string, maxzoom: number, paint: any = {}) => {
        const r = raster(id, tiles, maxzoom);
        m.addSource(id, r.source); m.addLayer({ id, type: "raster", source: id, paint: { "raster-fade-duration": 200, ...paint } });
      };
      add("sat", `${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`, 8);
      add("day", `${GIBS}/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/${fireDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`, 9);
      add("night", `${GIBS}/VIIRS_Black_Marble/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`, 8);
      m.addSource("countries", { type: "geojson", data, generateId: false });
      m.addLayer({ id: "pop", type: "fill", source: "countries", paint: { "fill-opacity": 0.55, "fill-color": ["step", ["to-number", ["get", "POP_EST"]], "#0b1f3a", 1e6, "#17407a", 1e7, "#2d6cb5", 5e7, "#6fa8dc", 2e8, "#e8f1fb"] } });
      m.addLayer({ id: "hit", type: "fill", source: "countries", paint: { "fill-color": "#000", "fill-opacity": 0 } });
      m.addLayer({ id: "sel", type: "fill", source: "countries", filter: ["==", ["get", "ADM0_A3"], ""], paint: { "fill-color": "#ffffff", "fill-opacity": 0.18 } });
      m.addLayer({ id: "bnd", type: "line", source: "countries", paint: { "line-color": contColor, "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.8, 6, 2], "line-opacity": 0.95 } });
      add("fire", `${GIBS}/VIIRS_NOAA20_Thermal_Anomalies_375m_All/default/${fireDate}/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`, 8);
      const pts: FC = { type: "FeatureCollection", features: data.features.map((f) => {
        const b = bboxOf(bigPoly(f.geometry)); return { type: "Feature", properties: f.properties, geometry: { type: "Point", coordinates: [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2] } }; }) };
      m.addSource("labels", { type: "geojson", data: pts });
      m.addLayer({ id: "lab", type: "symbol", source: "labels", layout: {
        "text-field": ["coalesce", ["get", "NAME_PT"], ["get", "NAME"]], "text-font": ["Open Sans Regular"], "text-size": ["interpolate", ["linear"], ["zoom"], 1, 9, 5, 13],
        "symbol-sort-key": ["-", 0, ["to-number", ["get", "POP_EST"]]] }, paint: { "text-color": "#eaf2ff", "text-halo-color": "#02060d", "text-halo-width": 1.4 } });
      setReady(true);
    });
    m.on("click", (e) => {
      const f = m.queryRenderedFeatures(e.point, { layers: ["hit"] })[0];
      if (!f) return;
      const p = f.properties as Country;
      const full = data.features.find((x) => (x.properties as Country).ADM0_A3 === p.ADM0_A3)!;
      setSel({ p: full.properties as Country, bbox: bboxOf((full.geometry as any).coordinates) });
    });
    m.on("mousemove", (e) => { if (coord.current) coord.current.textContent = `${e.lngLat.lat.toFixed(1)}° N, ${e.lngLat.lng.toFixed(1)}° E`; });
    return () => m.remove();
  }, [data]);

  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    const run = () => { for (const [k] of LAYERS) m.setLayoutProperty(k, "visibility", on[k] ? "visible" : "none"); };
    run();
  }, [on, ready]);
  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    const run = () => m.setFilter("sel", ["==", ["get", "ADM0_A3"], sel?.p.ADM0_A3 ?? ""]);
    run();
    if (sel) { const b = sel.bbox; m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 80, duration: 1200, maxZoom: 6 }); }
  }, [sel, ready]);

  const pickCountry = (f: FC["features"][number]) => { setSel({ p: f.properties, bbox: bboxOf(f.geometry.coordinates) }); setQ(""); input.current?.blur(); };
  // ponytail: busca só em países e coordenadas. Dados futuros entram como novas fontes aqui dentro.
  const hits: Hit[] = useMemo(() => {
    const t = q.trim();
    if (!t) return [];
    const c = COORD.exec(t);
    if (c) {
      const lat = +c[1].replace(",", "."), lon = +c[2].replace(",", ".");
      if (Math.abs(lat) > 90 || Math.abs(lon) > 180) return [];
      return [{ key: "xy", label: `Ir para ${lat}, ${lon}`, sub: "Coordenadas (lat, lon)", go: () => { map.current?.flyTo({ center: [lon, lat], zoom: 6, duration: 1500 }); setQ(""); input.current?.blur(); } }];
    }
    const n = norm(t);
    return (data?.features ?? [])
      .map((f) => ({ f, name: norm(String(f.properties.NAME_PT ?? f.properties.NAME)) }))
      .filter((x) => x.name.includes(n))
      .sort((a, b) => Number(b.name.startsWith(n)) - Number(a.name.startsWith(n)) || a.name.localeCompare(b.name))
      .slice(0, 6)
      .map(({ f }) => ({ key: f.properties.ADM0_A3, label: f.properties.NAME_PT ?? f.properties.NAME, sub: CONT[f.properties.CONTINENT]?.pt ?? f.properties.CONTINENT, go: () => pickCountry(f) }));
  }, [q, data]);
  useEffect(() => setHi(0), [q]);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "/" && document.activeElement?.tagName !== "INPUT") { e.preventDefault(); input.current?.focus(); } };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setHi((hi + 1) % Math.max(1, hits.length)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((hi + hits.length - 1) % Math.max(1, hits.length)); }
    else if (e.key === "Enter") hits[hi]?.go();
    else if (e.key === "Escape") { setQ(""); input.current?.blur(); }
  };

  const goRegion = (r: string) => {
    setRegion(r); setSel(undefined);
    const v = r === "World" ? [0, 10, 1.6] : CONT[r].view;
    map.current?.easeTo({ center: [v[0], v[1]], zoom: v[2], duration: 1200 });
  };
  const togglePitch = () => { map.current?.easeTo({ pitch: pitch3d ? 0 : 60, duration: 800 }); setPitch3d(!pitch3d); };
  const Head = ({ k, t }: { k: keyof typeof open; t: string }) => (
    <button className="gx-head" aria-expanded={open[k]} onClick={() => setOpen({ ...open, [k]: !open[k] })}><span>{t}</span><i>{open[k] ? "▾" : "▸"}</i></button>
  );

  return (
    <div className="gx">
      <div ref={el} className="gx-map" role="application" aria-label="Globo interativo. Clique num país para ver detalhes." />
      {!data && <p className="gx-load">Carregando fronteiras…</p>}

      <div className="gx-hero">
        <span className="gx-logo" aria-hidden>◐</span>
        <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKey} onFocus={() => setFocus(true)} onBlur={() => setTimeout(() => setFocus(false), 120)}
          placeholder="Pesquisar países ou coordenadas (ex.: -15.8, -47.9)" role="combobox" aria-expanded={focus && hits.length > 0} aria-controls="gx-hits" aria-autocomplete="list" aria-label="Pesquisar" />
        <kbd aria-hidden>/</kbd>
        {focus && q.trim() && (
          <ul id="gx-hits" role="listbox" className="gx-hits">
            {hits.length ? hits.map((h, i) => (
              <li key={h.key} role="option" aria-selected={i === hi} className={i === hi ? "on" : ""} onMouseDown={(e) => { e.preventDefault(); h.go(); }} onMouseEnter={() => setHi(i)}>
                <b>{h.label}</b><small>{h.sub}</small></li>)) : <li className="none">Nada encontrado</li>}
          </ul>)}
      </div>

      <aside className="gx-left">
        <section className="panel"><Head k="layers" t="Camadas" />
          {open.layers && <ul className="gx-list">{LAYERS.map(([k, t]) => (
            <li key={k}><label><span>{t}</span><input type="checkbox" role="switch" checked={on[k]} onChange={(e) => setOn({ ...on, [k]: e.target.checked })} /><i className="sw" /></label></li>))}</ul>}
          {open.layers && <p className="gx-note">Imagens: NASA GIBS (focos de {fireDate}). Fronteiras: Natural Earth.</p>}
        </section>
      </aside>

      <aside className="gx-right">
        <section className="panel"><Head k="reg" t={sel ? "País selecionado" : "Foco regional"} />
          {open.reg && (sel ? (
            <div>
              <p className="gx-big">{sel.p.NAME_PT ?? sel.p.NAME}</p>
              <dl className="gx-dl"><dt>Continente</dt><dd>{CONT[sel.p.CONTINENT]?.pt ?? sel.p.CONTINENT}</dd><dt>População</dt><dd>{nf(sel.p.POP_EST)}</dd></dl>
              <button className="gx-link" onClick={() => setSel(undefined)}>Limpar seleção</button>
            </div>
          ) : (
            <div>
              <select value={region} onChange={(e) => goRegion(e.target.value)} aria-label="Região">
                <option value="World">Mundo</option>{ORDER.map((k) => <option key={k} value={k}>{CONT[k].pt}</option>)}</select>
              <p className="gx-note">Clique num país no globo para ver detalhes.</p>
            </div>))}
        </section>
      </aside>

      <div className="gx-tools">
        <button aria-label="Aproximar" onClick={() => map.current?.zoomIn()}>+</button>
        <button aria-label="Afastar" onClick={() => map.current?.zoomOut()}>−</button>
        <button aria-label="Norte para cima" onClick={() => map.current?.easeTo({ bearing: 0, pitch: 0 })}>N</button>
        <button aria-pressed={pitch3d} onClick={togglePitch}>3D</button>
      </div>
      <div className="gx-coord"><span ref={coord}>–</span></div>

    </div>
  );
}
