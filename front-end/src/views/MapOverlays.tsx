import type { LayerResponseDTO } from "../api/dto";
import { monthName, num, t } from "../i18n";

/** Badge da camada, seletor (previsão/IPP), legenda com rótulos (RF-UI-02). */
export function MapOverlays({ hz, kind, setKind, layer, busy, res, month, satellite, setSatellite, compact }: {
  hz: number; kind: "forecast" | "ipp"; setKind: (k: "forecast" | "ipp") => void; layer?: LayerResponseDTO; busy: boolean;
  res: number | null; month?: string | null; satellite: boolean; setSatellite: (v: boolean) => void; compact: boolean;
}) {
  const lyr = hz === 0 ? "history" : kind;
  const left = compact ? 396 : 12;
  const right = compact ? 552 : 12;
  const cuts = layer?.cuts;
  return (
    <>
      <div className="pnl badge ov-badge" style={{ left, top: 12, maxWidth: `calc(100% - ${left + right}px)` }} aria-live="polite">
        <span className={`dot${busy ? " off" : ""}`} /><b>{t(`map.badge.${lyr}`, { month: monthName(month, "short") })}</b>
        <span>{busy ? t("map.loading") : res ? t("map.hex", { r: res }) : t("map.square")}</span>
      </div>
      <div className="pnl ctrl ov-ctrl" style={{ right, top: 52 }}>
        <span className="lbl">{t("layer.title")}</span>
        {(["forecast", "ipp"] as const).map((k) => (
          <button key={k} className="tg" role="switch" aria-checked={hz !== 0 && kind === k} disabled={hz === 0} onClick={() => setKind(k)}>
            {t(`layer.${k}`)}<span className="sw" /></button>))}
        <button className="tg" role="switch" aria-checked={hz === 0} disabled>{t("layer.history")}<span className="sw" /></button>
        <button className="tg" role="switch" aria-checked={satellite} onClick={() => setSatellite(!satellite)}>{t("layer.satellite")}<span className="sw" /></button>
      </div>
      <div className="pnl legend ov-legend" style={{ right, bottom: 40 }}>
        <span className="lbl">{t(`legend.${lyr}`)}</span>
        <div className="steps">{[0, 1, 2, 3].map((k) => <i key={k} style={{ background: `var(--${lyr === "ipp" ? "p" : "c"}${k})` }} />)}</div>
        {lyr === "history" ? <div className="labs"><span>1</span><span>10</span><span>100</span><span>1000+</span></div> :
          <div className="labs">{(lyr === "ipp" ? ["baixo", "medio", "alto", "critico"] : ["baixo", "normal", "alto", "critico"]).map((l) =>
            <span key={l}>{t(`${lyr === "ipp" ? "ipp" : "lvlS"}.${l}`)}</span>)}</div>}
        <span className="muted">{lyr === "ipp" && cuts ? `${t("legend.ipp_note")} · ${num(cuts.medio, 2)} · ${num(cuts.alto, 2)} · ${num(cuts.critico, 2)}` : t(`legend.${lyr}_note`)}</span>
      </div>
    </>
  );
}
