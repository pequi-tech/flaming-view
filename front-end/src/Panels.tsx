import { CONT, LAYERS, ORDER, fireDate, type LayerKey } from "./config";
import { nf, type Selected } from "./geo";

const Panel = ({ title, open, onToggle, children }: { title: string; open: boolean; onToggle: () => void; children: React.ReactNode }) => (
  <section className="panel">
    <button className="gx-head" aria-expanded={open} onClick={onToggle}><span>{title}</span><i>{open ? "▾" : "▸"}</i></button>
    {open && children}
  </section>
);

export function LayersPanel({ on, setOn, open, onToggle }: { on: Record<LayerKey, boolean>; setOn: (v: Record<LayerKey, boolean>) => void; open: boolean; onToggle: () => void }) {
  return (
    <Panel title="Camadas" open={open} onToggle={onToggle}>
      <ul className="gx-list">{LAYERS.map(([k, t]) => (
        <li key={k}><label><span>{t}</span><input type="checkbox" role="switch" checked={on[k]} onChange={(e) => setOn({ ...on, [k]: e.target.checked })} /><i className="sw" /></label></li>))}</ul>
      <p className="gx-note">Imagens: NASA GIBS (focos de {fireDate}). Fronteiras: Natural Earth.</p>
    </Panel>
  );
}

export function RegionPanel({ sel, region, onRegion, onClear, open, onToggle }: { sel?: Selected; region: string; onRegion: (r: string) => void; onClear: () => void; open: boolean; onToggle: () => void }) {
  return (
    <Panel title={sel ? "País selecionado" : "Foco regional"} open={open} onToggle={onToggle}>
      {sel ? (
        <div>
          <p className="gx-big">{sel.p.NAME_PT ?? sel.p.NAME}</p>
          <dl className="gx-dl"><dt>Continente</dt><dd>{CONT[sel.p.CONTINENT]?.pt ?? sel.p.CONTINENT}</dd><dt>População</dt><dd>{nf(sel.p.POP_EST)}</dd></dl>
          <button className="gx-link" onClick={onClear}>Limpar seleção</button>
        </div>
      ) : (
        <div>
          <select value={region} onChange={(e) => onRegion(e.target.value)} aria-label="Região">
            <option value="World">Mundo</option>{ORDER.map((k) => <option key={k} value={k}>{CONT[k].pt}</option>)}</select>
          <p className="gx-note">Clique num país no globo para ver detalhes.</p>
        </div>
      )}
    </Panel>
  );
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
