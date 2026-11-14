import { useCallback, useEffect, useState } from "react";
import { CONT, type LayerKey } from "./config";
import { countryBounds, type FC, type Feature, type Selected } from "./geo";
import { useGlobeMap } from "./useGlobeMap";
import { useSearch } from "./useSearch";
import SearchBar from "./SearchBar";
import { LayersPanel, RegionPanel, Tools } from "./Panels";

export default function Globe() {
  const [data, setData] = useState<FC>();
  const [on, setOn] = useState<Record<LayerKey, boolean>>({ sat: true, day: false, night: false, fire: true, bnd: true, lab: true, pop: false });
  const [region, setRegion] = useState("World");
  const [sel, setSel] = useState<Selected>();
  const [pitch3d, setPitch3d] = useState(false);
  const [open, setOpen] = useState({ layers: true, reg: true });

  useEffect(() => { fetch("/data/countries.geojson").then((r) => r.json()).then(setData); }, []);

  const { el, map, coord } = useGlobeMap(data, on, sel, setSel);
  const pickCountry = useCallback((f: Feature) => setSel({ p: f.properties, bbox: countryBounds(f.geometry) }), []);
  const search = useSearch(data, map, pickCountry);

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
        <LayersPanel on={on} setOn={setOn} open={open.layers} onToggle={() => setOpen({ ...open, layers: !open.layers })} />
      </aside>
      <aside className="gx-right">
        <RegionPanel sel={sel} region={region} onRegion={goRegion} onClear={() => setSel(undefined)} open={open.reg} onToggle={() => setOpen({ ...open, reg: !open.reg })} />
      </aside>
      <Tools pitch3d={pitch3d} onZoom={(d) => (d > 0 ? map.current?.zoomIn() : map.current?.zoomOut())} onNorth={() => map.current?.easeTo({ bearing: 0, pitch: 0 })} onPitch={togglePitch} />
      <div className="gx-coord"><span ref={coord}>–</span></div>
    </div>
  );
}
