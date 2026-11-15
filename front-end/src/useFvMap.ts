import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { cellToBoundary } from "h3-js";
import { GIBS } from "./config";
import type { LayerResponseDTO } from "./api/dto";

maplibregl.setWorkerUrl(workerUrl);

export const CLASS_COLOR = ["#9a5030", "#b4582c", "#ea7f3c", "#ffb27d"];      // Fogo previsto (laranja)
export const PRIORITY_COLOR = ["#5f6f8a", "#8193b3", "#aebfdc", "#e3ecfb"];   // Prioridade/IPP (azul-acinzentado)
const ORD: Record<string, number> = { baixo: 0, normal: 1, medio: 1, alto: 2, critico: 3 };
const FLAT = new Set(["state", "municipality"]);

/** Resolução H3 pelo zoom (A2): 4 → 5 → 6 → células 0,05° (null). */
export const resForZoom = (z: number) => (z < 4.5 ? 4 : z < 6 ? 5 : z < 7.6 ? 6 : null);

function toFeatures(data: LayerResponseDTO) {
  const features = data.cells.map((c) => {
    let ring: number[][];
    if (data.shape === "h3" && c.id) ring = cellToBoundary(c.id, true);
    else ring = [[c.lon, c.lat], [c.lon + 0.05, c.lat], [c.lon + 0.05, c.lat + 0.05], [c.lon, c.lat + 0.05], [c.lon, c.lat]];
    if (ring.length && (ring[0][0] !== ring.at(-1)![0] || ring[0][1] !== ring.at(-1)![1])) ring = [...ring, ring[0]];
    const k = c.level ? ORD[c.level] ?? 1 : -1;
    return { type: "Feature" as const, properties: { id: c.id, value: c.value, k, ipp: data.layer === "ipp" ? 1 : 0 }, geometry: { type: "Polygon" as const, coordinates: [ring] } };
  });
  return { type: "FeatureCollection" as const, features };
}

/** Um só mapa (A14): globo no país/mundo, plano em estado/município; camada de células e contorno da área. */
export function useFvMap(opts: { geometry?: any; bbox?: [number, number, number, number]; level?: string; layer?: LayerResponseDTO;
  onPick: (lngLat: { lng: number; lat: number }) => void; onZoom: (z: number, bounds: [number, number, number, number]) => void; satellite: boolean }) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const [ready, setReady] = useState(false);
  const cb = useRef(opts); cb.current = opts;

  useEffect(() => {
    const m = new maplibregl.Map({
      container: el.current!, center: [-52, -14], zoom: 3, attributionControl: { compact: true }, maxPitch: 0,
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#050a14" } }],
        sky: { "atmosphere-blend": 0.8, "sky-color": "#0b1f44", "horizon-color": "#2a5cb8", "sky-horizon-blend": 0.5 } as any },
    });
    map.current = m;
    m.on("error", (e) => { const s = String(e.error?.message ?? ""); if (!/404|AJAXError|Failed to fetch/.test(s)) console.warn("maplibre:", s); });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.on("load", () => {
      m.setProjection({ type: "globe" });
      m.addSource("sat", { type: "raster", tiles: [`${GIBS}/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`], tileSize: 256, maxzoom: 8, attribution: "NASA GIBS" });
      m.addLayer({ id: "sat", type: "raster", source: "sat", paint: { "raster-brightness-max": 0.42, "raster-saturation": -0.55 } });
      m.addSource("countries", { type: "geojson", data: "/data/countries.geojson" });
      m.addLayer({ id: "countries", type: "line", source: "countries", paint: { "line-color": "rgba(148,178,220,.28)", "line-width": 0.6 } });
      m.addSource("cells", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "cells", type: "fill", source: "cells", paint: {
        "fill-color": ["case", ["<", ["get", "k"], 0],
          ["interpolate", ["linear"], ["log10", ["+", 1, ["get", "value"]]], 0, CLASS_COLOR[0], 1, CLASS_COLOR[1], 2, CLASS_COLOR[2], 3, CLASS_COLOR[3]],
          ["==", ["get", "ipp"], 1], ["match", ["get", "k"], 0, PRIORITY_COLOR[0], 1, PRIORITY_COLOR[1], 2, PRIORITY_COLOR[2], PRIORITY_COLOR[3]],
          ["match", ["get", "k"], 0, CLASS_COLOR[0], 1, CLASS_COLOR[1], 2, CLASS_COLOR[2], CLASS_COLOR[3]]],
        "fill-opacity": ["case", ["<", ["get", "k"], 0], 0.8, ["match", ["get", "k"], 0, 0.35, 1, 0.55, 2, 0.8, 0.95]],
        "fill-opacity-transition": { duration: 500 }, "fill-color-transition": { duration: 500 } } });
      m.addLayer({ id: "cells-line", type: "line", source: "cells", paint: { "line-color": "rgba(5,10,20,.55)", "line-width": 0.4 } });
      m.addLayer({ id: "crit-glow", type: "line", source: "cells", filter: ["==", ["get", "k"], 3],
        paint: { "line-color": ["case", ["==", ["get", "ipp"], 1], "#ffffff", "#ffd4b5"], "line-width": 1.2, "line-blur": 1.5, "line-opacity": 0.8 } });
      m.addSource("area", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      m.addLayer({ id: "area-glow", type: "line", source: "area", paint: { "line-color": "#4c8dff", "line-width": 6, "line-blur": 6, "line-opacity": 0.35 } });
      m.addLayer({ id: "area", type: "line", source: "area", paint: { "line-color": "#9cc2ff", "line-width": 1.4 } });
      setReady(true);
    });
    const zoomed = () => { const b = m.getBounds(); cb.current.onZoom(m.getZoom(), [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()]); };
    m.on("moveend", zoomed);
    m.on("click", (e) => cb.current.onPick(e.lngLat));
    m.on("mousemove", "cells", () => { m.getCanvas().style.cursor = "pointer"; });
    m.on("mouseleave", "cells", () => { m.getCanvas().style.cursor = ""; });
    return () => m.remove();
  }, []);

  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    (m.getSource("area") as maplibregl.GeoJSONSource).setData(opts.geometry ? { type: "Feature", properties: {}, geometry: opts.geometry } : { type: "FeatureCollection", features: [] });
    m.setProjection({ type: FLAT.has(opts.level ?? "") ? "mercator" : "globe" });
    if (opts.bbox) {
      const w = m.getContainer().clientWidth;            // painel à esquerda só cabe em tela larga
      const left = w > 1000 ? 360 : 40;
      m.fitBounds([[opts.bbox[0], opts.bbox[1]], [opts.bbox[2], opts.bbox[3]]], { padding: { top: 60, bottom: 60, left, right: 40 }, duration: 1400, maxZoom: 9 });
    }
  }, [opts.geometry, opts.bbox, opts.level, ready]);

  useEffect(() => {
    const m = map.current; if (!m || !ready) return;
    (m.getSource("cells") as maplibregl.GeoJSONSource).setData(opts.layer ? toFeatures(opts.layer) : { type: "FeatureCollection", features: [] });
  }, [opts.layer, ready]);

  useEffect(() => { const m = map.current; if (m && ready) m.setLayoutProperty("sat", "visibility", opts.satellite ? "visible" : "none"); }, [opts.satellite, ready]);

  return { el, map, ready };
}
