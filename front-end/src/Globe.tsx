import { useCallback, useEffect, useState } from "react";
import { CONT, type LayerKey } from "./config";
import { countryBounds, type FC, type Feature, type Selected } from "./geo";
import { useGlobeMap } from "./useGlobeMap";
import { useSearch } from "./useSearch";
import SearchBar from "./SearchBar";
import { LayersPanel, MethodSection, RegionPanel, Tools } from "./Panels";
import { useFireData } from "./api/useFireData";

export default function Globe() {
  const [data, setData] = useState<FC>();
  const [on, setOn] = useState<Record<LayerKey, boolean>>({ sat: true, day: false, night: false, fire: true, history: true, bnd: true, lab: true, pop: false });
  const [region, setRegion] = useState("World");
  const [sel, setSel] = useState<Selected>();
  const [period, setPeriod] = useState({ year: new Date().getFullYear() - 1, month: new Date().getMonth() + 1, resolution: 1 as 0.25 | 0.5 | 1 | 2 });
  const [pitch3d, setPitch3d] = useState(false);
  const [open, setOpen] = useState({ layers: true, reg: true, method: false });

  useEffect(() => { fetch("/data/countries.geojson").then((r) => r.json()).then(setData); }, []);

  const fireData = useFireData(sel?.bbox, { year: period.year, month: period.month, res: period.resolution }, on.history);
  const { el, map, coord } = useGlobeMap(data, on, sel, setSel,
    fireData.cells.status === "loaded" ? fireData.cells.data : undefined);
  const pickCountry = useCallback((f: Feature) => setSel({ p: f.properties, bbox: countryBounds(f.geometry) }), []);
  const search = useSearch(data, map, pickCountry);

  useEffect(() => {
    if (fireData.backend.status !== "online") return;
    const years = fireData.backend.health.years;
    const first = years[0]; const last = years.at(-1);
    if (first === undefined || last === undefined) return;
    setPeriod((current) => ({ ...current, year: Math.max(first, Math.min(last, current.year)) }));
  }, [fireData.backend]);

  const goRegion = (r: string) => {
    setRegion(r); setSel(undefined);
    const v = r === "World" ? [0, 10, 1.6] : CONT[r].view;
    map.current?.easeTo({ center: [v[0], v[1]], zoom: v[2], duration: 1200 });
  };
  const togglePitch = () => { map.current?.easeTo({ pitch: pitch3d ? 0 : 60, duration: 800 }); setPitch3d(!pitch3d); };

  return (
    <div className="gx">
      <div ref={el} className="gx-map" role="application" aria-label="Globo interativo. Clique num país para ver detalhes." />
      {!data && <p className="gx-load">Carregando fronteiras…</p>}
      <SearchBar s={search} />
      <aside className="gx-left">
        <LayersPanel on={on} setOn={setOn} open={open.layers} onToggle={() => setOpen({ ...open, layers: !open.layers })}
          backend={fireData.backend} year={period.year} month={period.month} resolution={period.resolution}
          onYear={(year) => setPeriod((current) => ({ ...current, year }))}
          onMonth={(month) => setPeriod((current) => ({ ...current, month }))}
          onResolution={(resolution) => setPeriod((current) => ({ ...current, resolution }))} />
      </aside>
      <aside className="gx-right">
        <RegionPanel sel={sel} region={region} onRegion={goRegion} onClear={() => setSel(undefined)} open={open.reg} onToggle={() => setOpen({ ...open, reg: !open.reg })}
          backend={fireData.backend} fireData={fireData.country} year={period.year} month={period.month}
          cellData={fireData.cells}
          onPeriod={(year, month) => setPeriod((current) => ({ ...current, year, month }))} />
        <MethodSection open={open.method} onToggle={() => setOpen({ ...open, method: !open.method })} backend={fireData.backend} method={fireData.method} />
      </aside>
      <Tools pitch3d={pitch3d} onZoom={(d) => (d > 0 ? map.current?.zoomIn() : map.current?.zoomOut())} onNorth={() => map.current?.easeTo({ bearing: 0, pitch: 0 })} onPitch={togglePitch} />
      <div className="gx-coord"><span ref={coord}>–</span></div>
    </div>
  );
}
