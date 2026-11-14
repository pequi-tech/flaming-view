import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { GIBS, LAYERS, contColor, fireDate, type LayerKey } from "./config";
import { bboxOf, bigPoly, countryBounds, type Country, type FC, type Selected } from "./geo";

maplibregl.setWorkerUrl(workerUrl);

const raster = (id: string, tiles: string, maxzoom: number, attribution = "NASA GIBS") =>
  ({ id, source: { type: "raster" as const, tiles: [tiles], tileSize: 256, maxzoom, attribution } });

/** Builds the globe once `data` is loaded; keeps layer visibility and the selected country in sync. */
export function useGlobeMap(data: FC | undefined, on: Record<LayerKey, boolean>, sel: Selected | undefined, onSelect: (s: Selected) => void) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const coord = useRef<HTMLSpanElement>(null);
  const [ready, setReady] = useState(false);
  const select = useRef(onSelect);
  select.current = onSelect;

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
      const full = data.features.find((x) => (x.properties as Country).ADM0_A3 === (f.properties as Country).ADM0_A3)!;
      select.current({ p: full.properties as Country, bbox: countryBounds(full.geometry) });
    });
    m.on("mousemove", (e) => {
      const { lat, lng } = e.lngLat.wrap();
      if (coord.current) coord.current.textContent = `${Math.abs(lat).toFixed(1)}° ${lat < 0 ? "S" : "N"}, ${Math.abs(lng).toFixed(1)}° ${lng < 0 ? "W" : "E"}`;
    });
    return () => m.remove();
  }, [data]);

  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    for (const [k] of LAYERS) m.setLayoutProperty(k, "visibility", on[k] ? "visible" : "none");
  }, [on, ready]);

  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    m.setFilter("sel", ["==", ["get", "ADM0_A3"], sel?.p.ADM0_A3 ?? ""]);
    if (sel) { const b = sel.bbox; m.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 80, duration: 1200, maxZoom: 6 }); }
  }, [sel, ready]);

  return { el, map, coord };
}
