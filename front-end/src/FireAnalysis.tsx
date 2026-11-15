import { useState } from "react";
import { fireApi, ApiError } from "./api/client";
import type { CalendarMonthDTO } from "./api/dto";
import type { BackendStatus, CellDataStatus, CountryFireData } from "./api/useFireData";
import { nf, type Selected } from "./geo";
import { CalendarHeatmap, SeasonChart, SeriesChart } from "./FireCharts";

const MONTHS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

export function AnalysisControls({ backend, year, month, resolution, onYear, onMonth, onResolution }: {
  backend: BackendStatus; year: number; month: number; resolution: 0.25 | 0.5 | 1 | 2;
  onYear: (value: number) => void; onMonth: (value: number) => void; onResolution: (value: 0.25 | 0.5 | 1 | 2) => void;
}) {
  const years = backend.status === "online" ? backend.health.years : [];
  const firstYear = years[0] ?? year;
  const lastYear = years.at(-1) ?? year;
  return (
    <div className="fire-controls">
      <label>Ano histórico<select value={year} disabled={backend.status !== "online"} onChange={(e) => onYear(Number(e.target.value))}>
        {Array.from({ length: Math.max(1, lastYear - firstYear + 1) }, (_, i) => lastYear - i).map((option) => <option key={option} value={option}>{option}</option>)}
      </select></label>
      <label>Mês<select value={month} onChange={(e) => onMonth(Number(e.target.value))}>
        {MONTHS.map((name, i) => <option key={name} value={i + 1}>{name}</option>)}
      </select></label>
      <label>Resolução das células<select value={resolution} onChange={(e) => onResolution(Number(e.target.value) as 0.25 | 0.5 | 1 | 2)}>
        {[0.25, 0.5, 1, 2].map((value) => <option key={value} value={value}>{value}°</option>)}
      </select></label>
    </div>
  );
}

function ActivityCard({ entry, unit }: { entry?: CalendarMonthDTO; unit: string }) {
  if (!entry) return <div className="fire-stat"><small>Atividade selecionada</small><b>—</b><span>Sem dado no período</span></div>;
  return <div className={`fire-stat level-${entry.level}`}>
    <small>Atividade · {MONTHS[entry.month - 1]} {entry.year}</small>
    <b>{nf(entry.value)}</b><span>{unit}</span>
    <div className="fire-stat-meta">Mediana {nf(entry.median)} · p75 {nf(entry.p75)} · p90 {nf(entry.p90)}{entry.ratio !== null ? ` · ${entry.ratio.toFixed(1)}×` : ""}</div>
    {entry.estimated && <em>Estimativa harmonizada</em>}
  </div>;
}

function CurrentCard({ backend, data }: { backend: BackendStatus; data: Extract<CountryFireData, { status: "loaded" }> }) {
  if (backend.status === "online" && !backend.health.realtime) return <div className="fire-current fire-current-muted"><small>Tempo real NRT</small><b>Indisponível</b><span>Configure FIRMS_MAP_KEY no backend para consultar o mês atual.</span></div>;
  if (!data.current) return <div className="fire-current fire-current-muted"><small>Tempo real NRT</small><b>Não consultado</b><span>{data.currentError ?? "Aguardando configuração da conexão."}</span></div>;
  const current = data.current;
  return <div className={`fire-current level-${current.level}`}>
    <small>Mês atual · {String(current.month).padStart(2, "0")}/{current.year}</small>
    <b>{nf(current.value_to_date)}</b><span>até hoje · projeção {nf(current.projected)}</span>
    <div className="fire-current-meta">Mediana {nf(current.median)} · p75 {nf(current.p75)} · p90 {nf(current.p90)} · razão {current.ratio === null ? "—" : `${current.ratio.toFixed(1)}×`}</div>
    <em>{current.level} · {current.satellite}{current.stale ? " · snapshot em cache" : ""}</em>
  </div>;
}

function downloadName(area: string) {
  return `calendario-fogo-${area.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}.csv`;
}

export function FireAnalysis({ sel, backend, data, cellData, year, month, onPeriod }: {
  sel: Selected; backend: BackendStatus; data: CountryFireData; cellData: CellDataStatus; year: number; month: number;
  onPeriod: (year: number, month: number) => void;
}) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const loaded = data.status === "loaded" ? data : undefined;
  const selected = loaded?.calendar.months.find((entry) => entry.year === year && entry.month === month);

  const exportCalendar = async () => {
    setExporting(true); setExportError("");
    try {
      const blob = await fireApi.calendarCsv({ bbox: sel.bbox,
        from_year: loaded?.calendar.baseline_years[0], to_year: loaded?.calendar.baseline_years.at(-1) });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url; link.download = downloadName(sel.p.NAME_PT ?? sel.p.NAME ?? sel.p.ADM0_A3); link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      setExportError(error instanceof ApiError ? error.message : "Não foi possível exportar o calendário.");
    } finally { setExporting(false); }
  };

  return (
    <div className="fire-analysis">
      <div className="fire-section-heading"><div><small>Arquivo histórico</small><b>Explorar atividade</b></div>
        <button className="fire-export" type="button" disabled={!loaded || exporting} onClick={exportCalendar}>{exporting ? "Gerando…" : "↓ CSV"}</button>
      </div>
      {data.status === "loading" && <p className="fire-feedback">Consultando calendário, série e mapa de células…</p>}
      {data.status === "error" && <p className="fire-feedback is-error">{data.message}</p>}
      {loaded && <>
        <div className="fire-stat-grid"><ActivityCard entry={selected} unit={loaded.calendar.unit} /><CurrentCard backend={backend} data={loaded} /></div>
        {cellData.status === "loading" && <p className="fire-feedback">Marcando células históricas no mapa…</p>}
        {cellData.status === "error" && <p className="fire-feedback is-error">Mapa histórico: {cellData.message}</p>}
        {cellData.status === "loaded" && <p className="fire-feedback">{cellData.data.cells.length.toLocaleString("pt-BR")} células marcadas · {cellData.data.res}° · pontos agregados, não focos individuais.</p>}
        <section className="fire-section"><h3>Calendário mensal</h3><p className="gx-note">Clique em um mês para atualizar o mapa e o resumo.</p>
          <CalendarHeatmap data={loaded.calendar} year={year} month={month} onSelect={onPeriod} />
        </section>
        <section className="fire-section"><h3>Série anual · faixa de incerteza</h3><SeriesChart data={loaded.series} /></section>
        <section className="fire-section"><h3>Sazonalidade típica</h3><SeasonChart data={loaded.calendar} /></section>
      </>}
      {exportError && <p className="fire-feedback is-error">{exportError}</p>}
    </div>
  );
}
