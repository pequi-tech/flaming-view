import { CONT, LAYERS, ORDER, fireDate, type LayerKey } from "./config";
import { nf, type Selected } from "./geo";
import type { BackendStatus, CellDataStatus, CountryFireData, MethodStatus } from "./api/useFireData";
import { AnalysisControls, FireAnalysis } from "./FireAnalysis";
import { MethodPanel } from "./MethodPanel";

const Panel = ({ title, open, onToggle, children }: { title: string; open: boolean; onToggle: () => void; children: React.ReactNode }) => (
  <section className="panel">
    <button className="gx-head" aria-expanded={open} onClick={onToggle}><span>{title}</span><i>{open ? "▾" : "▸"}</i></button>
    {open && children}
  </section>
);

export function LayersPanel({ on, setOn, open, onToggle, backend, year, month, resolution, onYear, onMonth, onResolution }: {
  on: Record<LayerKey, boolean>; setOn: (v: Record<LayerKey, boolean>) => void; open: boolean; onToggle: () => void;
  backend: BackendStatus; year: number; month: number; resolution: 0.25 | 0.5 | 1 | 2;
  onYear: (value: number) => void; onMonth: (value: number) => void; onResolution: (value: 0.25 | 0.5 | 1 | 2) => void;
}) {
  return (
    <>
      <Panel title="Camadas do mapa" open={open} onToggle={onToggle}>
        <ul className="gx-list">{LAYERS.map(([key, title]) => (
          <li key={key}><label><span>{title}</span><input type="checkbox" role="switch" checked={on[key]} onChange={(e) => setOn({ ...on, [key]: e.target.checked })} /><i className="sw" /></label></li>))}</ul>
        <p className="gx-note">NASA GIBS: focos recentes de {fireDate}. O histórico do backend mostra células agregadas, não focos individuais.</p>
        {on.history && <div className="history-legend" aria-label="Legenda da atividade agregada">
          <span><i className="history-1" />&lt; 10</span><span><i className="history-2" />10–99</span>
          <span><i className="history-3" />100–999</span><span><i className="history-4" />1 mil–9,9 mil</span><span><i className="history-5" />≥ 10 mil</span>
          <small>células-dia equivalentes por célula</small>
        </div>}
      </Panel>
      <section className="panel">
        <h2 className="fire-panel-label">Período e resolução</h2>
        <AnalysisControls backend={backend} year={year} month={month} resolution={resolution} onYear={onYear} onMonth={onMonth} onResolution={onResolution} />
        <p className="gx-note">Selecione um país para consultar e marcar a atividade histórica.</p>
      </section>
    </>
  );
}

export function RegionPanel({ sel, region, onRegion, onClear, open, onToggle, backend, fireData, cellData, year, month, onPeriod }: {
  sel?: Selected; region: string; onRegion: (r: string) => void; onClear: () => void;
  open: boolean; onToggle: () => void; backend: BackendStatus; fireData: CountryFireData; cellData: CellDataStatus;
  year: number; month: number;
  onPeriod: (year: number, month: number) => void;
}) {
  return (
    <Panel title={sel ? "Análise da área" : "Foco regional"} open={open} onToggle={onToggle}>
      {sel ? <div>
        <p className="gx-big">{sel.p.NAME_PT ?? sel.p.NAME}</p>
        <dl className="gx-dl"><dt>Continente</dt><dd>{CONT[sel.p.CONTINENT]?.pt ?? sel.p.CONTINENT}</dd><dt>População</dt><dd>{nf(sel.p.POP_EST)}</dd></dl>
        <FireAnalysis sel={sel} backend={backend} data={fireData} cellData={cellData} year={year} month={month} onPeriod={onPeriod} />
        <button className="gx-link" onClick={onClear}>Limpar seleção</button>
      </div> : <div>
        <select value={region} onChange={(e) => onRegion(e.target.value)} aria-label="Região">
          <option value="World">Mundo</option>{ORDER.map((key) => <option key={key} value={key}>{CONT[key].pt}</option>)}
        </select>
        <p className="gx-note">Clique em um país no globo ou pesquise pelo nome para abrir o calendário, a série e as marcações de atividade.</p>
        {backend.status === "online" && <p className="gx-note">API conectada · release {backend.health.release}</p>}
        {backend.status === "error" && <p className="gx-note">Backend indisponível: {backend.message}</p>}
      </div>}
    </Panel>
  );
}

export function MethodSection({ open, onToggle, backend, method }: { open: boolean; onToggle: () => void; backend: BackendStatus; method: MethodStatus }) {
  return <Panel title="Dados e método" open={open} onToggle={onToggle}><MethodPanel backend={backend} method={method} /></Panel>;
}

export function Tools({ pitch3d, onZoom, onNorth, onPitch }: { pitch3d: boolean; onZoom: (d: 1 | -1) => void; onNorth: () => void; onPitch: () => void }) {
  return (
    <div className="gx-tools">
      <button aria-label="Aproximar" onClick={() => onZoom(1)}>+</button>
      <button aria-label="Afastar" onClick={() => onZoom(-1)}>−</button>
      <button aria-label="Norte para cima" onClick={onNorth}>N</button>
      <button aria-pressed={pitch3d} onClick={onPitch}>3D</button>
    </div>
  );
}
