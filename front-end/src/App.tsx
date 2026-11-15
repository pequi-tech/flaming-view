import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, fireApi, fvApi } from "./api/client";
import type { AreaRef, CurrentResponseDTO, ForecastResponseDTO, LayerResponseDTO, MethodV2, PrioritiesResponseDTO } from "./api/dto";
import { countryBounds, type BBox } from "./geo";
import { monthName, setLang, t, useLang, type Lang } from "./i18n";
import { ICONS, installSpotlight } from "./ui";
import { decisionKey, useDecisions } from "./decisions";
import { resForZoom, useFvMap } from "./useFvMap";
import SearchBox from "./SearchBox";
import { MapOverlays } from "./views/MapOverlays";
import { Situation } from "./views/Situation";
import { Territory } from "./views/Territory";
import { Plan } from "./views/Plan";
import { Assistant } from "./views/Assistant";
import { Method } from "./views/Method";
import { Report } from "./views/Report";

export type View = "sit" | "map" | "ter" | "plan" | "rep" | "ia" | "met";
const NAV: [string, View[]][] = [["nav.monitor", ["sit", "map", "ter"]], ["nav.plan_group", ["plan", "rep"]], ["nav.support", ["ia", "met"]]];
const FULL = new Set<View>(["plan", "rep", "met"]);
export type Sort = "action" | "fire" | "ipp";
installSpotlight();                                   // só o cartão do IPP em Territórios usa .spot

const viewFromHash = (): View => (location.hash.slice(2).split("?")[0] as View) || "sit";
const hashParam = (k: string) => new URLSearchParams(location.hash.split("?")[1] ?? "").get(k);
export const cellIdAt = (lat: number, lon: number) => (Math.floor(lat * 20) + 1800) * 7200 + (Math.floor(lon * 20) + 3600);

export type AppCtx = {
  area: { id: string; level: string; name: string }; forecast?: ForecastResponseDTO; priorities?: PrioritiesResponseDTO; method?: MethodV2;
  horizon: number; cell: number | null; setCell: (id: number | null) => void; goArea: (id: string) => void; go: (v: View) => void;
  flyTo: (lat: number, lon: number, zoom?: number) => void; error?: string; current?: CurrentResponseDTO | null;
  sort: Sort; setSort: (s: Sort) => void;
};

export default function App() {
  const lang = useLang();
  const [view, setView] = useState<View>(viewFromHash);
  const [areaId, setAreaId] = useState(hashParam("area") ?? "BRA");
  const [forecast, setForecast] = useState<ForecastResponseDTO>();
  const [geo, setGeo] = useState<{ geometry: any; bbox: BBox }>();
  const [priorities, setPriorities] = useState<PrioritiesResponseDTO>();
  const [method, setMethod] = useState<MethodV2>();
  const [hz, setHz] = useState(1);                      // 0 = histórico do mês de emissão
  const [kind, setKind] = useState<"forecast" | "ipp">("ipp");
  const [satellite, setSatellite] = useState(true);
  const [view3, setView3] = useState<{ res: number | null; bounds?: BBox }>({ res: 4 });
  const [layer, setLayer] = useState<LayerResponseDTO>();
  const [layerBusy, setLayerBusy] = useState(false);
  const [cell, setCell] = useState<number | null>(hashParam("cell") ? Number(hashParam("cell")) : null);
  const [error, setError] = useState<string>();
  const [current, setCurrent] = useState<CurrentResponseDTO | null>();
  const [sort, setSort] = useState<Sort>("action");    // D-01: ação mais grave, desempate por fogo previsto
  const decisions = useDecisions();
  const horizon = Math.max(hz, 1);

  useEffect(() => { const f = () => { setView(viewFromHash()); const c = hashParam("cell"); if (c) setCell(Number(c)); const a = hashParam("area"); if (a) setAreaId(a); }; addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const go = useCallback((v: View) => { location.hash = `/${v}`; }, []);
  useEffect(() => { fvApi.method().then(setMethod).catch((e) => setError(e instanceof ApiError ? e.message : String(e))); }, []);

  useEffect(() => {
    const ab = new AbortController();
    setForecast(undefined); setPriorities(undefined); setGeo(undefined);
    fvApi.forecast({ area_id: areaId }, ab.signal).then(setForecast).catch((e) => !ab.signal.aborted && setError(e.message));
    fvApi.geometry(areaId, ab.signal).then((g) => setGeo({ geometry: g, bbox: countryBounds(g) })).catch(() => undefined);
    return () => ab.abort();
  }, [areaId]);

  useEffect(() => {
    const ab = new AbortController();
    fvApi.priorities({ area_id: areaId, horizon, limit: 1000, sort }, ab.signal).then(setPriorities).catch((e) => !ab.signal.aborted && setError(e.message));
    return () => ab.abort();
  }, [areaId, horizon, sort]);

  useEffect(() => {                                    // mês corrente FIRMS NRT (caixa da área); null = indisponível
    if (!geo) return;
    const ab = new AbortController();
    setCurrent(undefined);
    fireApi.current({ bbox: geo.bbox }, ab.signal).then(setCurrent).catch(() => !ab.signal.aborted && setCurrent(null));
    return () => ab.abort();
  }, [geo]);

  const issue = method?.model?.issue_month;
  useEffect(() => {
    const ab = new AbortController();
    const res = view3.res ?? (hz === 0 ? 6 : null);
    const lyr = hz === 0 ? "history" : kind;
    if (hz === 0 && !issue) return;
    const [y, m] = (issue ?? "2025-12").split("-").map(Number);
    setLayerBusy(true);
    fvApi.layer({ ...(res ? { area_id: areaId } : { bbox: view3.bounds }), layer: lyr, horizon, h3_res: res ?? undefined, year: y, month: m }, ab.signal)
      .then((d) => { setLayer(d); setLayerBusy(false); }).catch(() => !ab.signal.aborted && setLayerBusy(false));
    return () => ab.abort();
  }, [areaId, hz, kind, view3.res, view3.res === null ? view3.bounds?.join() : "", issue, horizon]);

  const mapApi = useFvMap({
    geometry: geo?.geometry, bbox: geo?.bbox, level: forecast?.area.level, layer, satellite,
    onPick: ({ lat, lng }) => { setCell(cellIdAt(lat, lng)); if (viewFromHash() === "sit" || viewFromHash() === "map") go("ter"); },
    onZoom: (z, b) => setView3((cur) => { const res = resForZoom(z); return cur.res === res && res !== null ? cur : { res, bounds: b }; }),
  });
  const flyTo = useCallback((lat: number, lon: number, zoom = 9) => mapApi.map.current?.flyTo({ center: [lon, lat], zoom, duration: 1400 }), [mapApi.map]);

  const area = forecast?.area ?? { id: areaId, name: areaId, level: "country" };
  const goArea = useCallback((id: string) => { setAreaId((cur) => { if (cur !== id) setCell(null); return id; }); }, []);
  const ctx: AppCtx = { area, forecast, priorities, method, horizon, cell, setCell, goArea, go, flyTo, error, current, sort, setSort };
  const h = forecast?.horizons.find((x) => x.horizon === horizon);

  const hzLabels = useMemo(() => [
    <>{monthName(issue, "short")} <small>{t("hz.history")}</small></>,
    ...[1, 2, 3].map((k) => <>{monthName(forecast?.horizons.find((x) => x.horizon === k)?.forecast_month, "short")} · M+{k}</>),
  ], [issue, forecast, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  // unidades com ação de severidade alta (R1/R7/R8) ainda não deliberada
  const pendingRecs = (priorities?.items ?? []).filter((i) => i.recommendations.some((r) => r.severity === "high"
    && !decisions[decisionKey(area.id, horizon, i.id, r.rule_id)])).length;
  return (
    <>
      <a className="sr" href="#main">Skip</a>
      <div className="gov" role="banner"><span className="flag" aria-hidden><i /><i /><i /></span><b>{t("gov.country")}</b><span>{t("gov.platform")}</span>
        <span className="sp" /><span>{t("gov.disclaimer")}</span></div>
      <aside className="side">
        <div className="logo"><span className="mk" aria-hidden><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c1.2 4.2 5.5 5.4 5.5 10.6a5.5 5.5 0 0 1-11 0c0-2.2 1-3.4 1-3.4s.2 3.2 2.4 3.2C9.9 8 12 6.6 12 2Z" /></svg></span>
          <div><b>Flaming View</b><small>{t("brand.tag")}</small></div></div>
        <nav className="nav" aria-label={t("nav.main")}>
          {NAV.map(([g, items]) => <div key={g} style={{ display: "contents" }}><div className="grp">{t(g)}</div>
            {items.map((v) => <a key={v} href={`#/${v}`} title={t(`nav.${v}`)} aria-current={view === v ? "page" : undefined}>{ICONS[v]}{t(`nav.${v}`)}
              {v === "plan" && pendingRecs > 0 && <span className="bd">{pendingRecs > 99 ? "99+" : pendingRecs}</span>}</a>)}</div>)}
        </nav>
        <div className="foot"><div className="rel">
          <div className="row between"><span><span className={`dot${method ? "" : " off"}`} />&nbsp; {method ? t("release.ok") : t("release.offline")}</span><b>{method?.release.slice(0, 8)}</b></div>
          {method && <div style={{ marginTop: 4 }}>{t("release.until", { month: monthName(issue, "short") })}</div>}
        </div></div>
      </aside>
      <header className="top">
        <SearchBox lineage={forecast?.lineage ?? [] as AreaRef[]} onArea={goArea} onCoord={(lat, lon) => { flyTo(lat, lon, 9); setCell(cellIdAt(lat, lon)); go("ter"); }} />
        <div className="seg" role="group" aria-label={t("hz.label")}>
          {hzLabels.map((label, i) => <button key={i} aria-pressed={hz === i} onClick={() => setHz(i)}>{label}</button>)}
        </div>
        <span className="sp" />
        <span className="pill hot">{t("top.critical")} <b className="num">{h?.classes.critico?.toLocaleString() ?? "—"}</b></span>
        <span className="lang" role="group" aria-label={t("lang.label")}>
          {(["pt-BR", "en"] as Lang[]).map((l) => <button key={l} aria-pressed={lang === l} onClick={() => setLang(l)}>{l === "en" ? "EN" : "PT"}</button>)}
        </span>
      </header>
      <main className="main" id="main">
        <div ref={mapApi.el} className="map" role="application" aria-label={t("map.label")} style={{ opacity: view === "ia" ? 0.55 : 1 }} />
        {!FULL.has(view) && <MapOverlays hz={hz} kind={kind} setKind={setKind} layer={layer} busy={layerBusy} res={view3.res}
          month={hz === 0 ? issue : h?.forecast_month} satellite={satellite} setSatellite={setSatellite} compact={view === "sit" || view === "ia" || cell !== null} />}
        {view === "sit" && <Situation ctx={ctx} />}
        {(view === "ter" || ((view === "sit" || view === "map") && cell !== null)) && <Territory ctx={ctx} />}
        {view === "ia" && <Assistant ctx={ctx} />}
        {view === "plan" && <Plan ctx={ctx} />}
        {view === "met" && <Method ctx={ctx} />}
        {view === "rep" && <Report ctx={ctx} />}
      </main>
    </>
  );
}
