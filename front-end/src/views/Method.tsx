import type { AppCtx } from "../App";
import { monthName, num, pct, t } from "../i18n";
import { Arc, useEntrance } from "../ui";

/** Método e fontes (RF-UI-09): tudo vem de /method. */
export function Method({ ctx }: { ctx: AppCtx }) {
  const m = ctx.method;
  const ref = useEntrance([!!m]);
  if (!m) return <div className="page muted">{ctx.error ? t("common.error", { msg: ctx.error }) : t("common.loading")}</div>;
  const mm = m.model;
  const hs = mm ? Object.entries(mm.horizons) : [];
  const imp = mm ? mm.horizons["1"].features.map((f, i) => [f, mm.horizons["1"].importances[i]] as const).sort((a, b) => b[1] - a[1]) : [];
  const max = imp[0]?.[1] ?? 1;
  const metrics = m.metrics as Record<string, number>;
  return (
    <div ref={ref} className="page met-grid" style={{ background: "var(--bg)", zIndex: 8, display: "grid", gridTemplateColumns: "1.25fr 1fr", gridAutoRows: "min-content" }}>
      <div style={{ gridColumn: "1 / -1" }}><div className="lbl" data-a>{t("met.label")}</div><div className="h1" data-a style={{ fontSize: 26 }}>{t("met.title")}</div></div>
      <div className="stack" style={{ gap: 14 }}>
        {mm && <div className="pnl static" style={{ padding: 16 }} data-a>
          <div className="row between"><span className="lbl">{t("met.auc", { a: mm.test_years[0], b: mm.test_years[1] })}</span><span className="muted">{t("met.auc_r")}</span></div>
          <div className="gauges" style={{ marginTop: 8 }}>{hs.map(([h, x]) =>
            <Arc key={h} small frac={((x.auc ?? 0.5) - 0.5) * 2} big={num(x.auc, 2)} caption={`M+${h}`} />)}</div>
        </div>}
        {mm && <div className="pnl static" style={{ padding: 16 }} data-a>
          <div className="row between"><span className="lbl">{t("met.top")}</span><span className="muted">{t("met.top_r")}</span></div>
          <div className="stack" style={{ gap: 9, marginTop: 12 }}>{hs.map(([h, x]) => <div key={h} className="stack" style={{ gap: 4 }}>
            <div className="cmp"><span>M+{h}</span><div className="b"><i style={{ "--w": `${(x.top10_precision ?? 0) * 100}%`, background: "var(--n)" } as React.CSSProperties} /></div><b className="num">{pct(x.top10_precision)}</b></div>
            <div className="cmp"><span className="muted">{t("met.base")}</span><div className="b"><i style={{ "--w": `${(x.base_rate ?? 0) * 100}%`, background: "rgba(148,178,220,.35)" } as React.CSSProperties} /></div><span className="num muted">{pct(x.base_rate)}</span></div>
            <div className="muted">{t("met.gain")}: {num(x.mae, 3)} vs {num(x.mae_baseline, 3)} ({x.gain !== null && x.gain >= 0 ? "+" : ""}{pct(x.gain, 1)})</div>
            {x.gain !== null && x.gain < 0 && <div className="warnband">{t("hz.weak", { month: `M+${h}` })}</div>}
          </div>)}</div>
        </div>}
        <div className="pnl static" style={{ padding: 16 }} data-a><span className="lbl">{t("met.not")}</span><div className="sub" style={{ marginTop: 8 }}>{t("met.not_t")}</div></div>
        <div className="pnl static" style={{ padding: 16 }} data-a>
          <span className="lbl">{t("met.model")}</span>
          {mm && <div className="sub" style={{ marginTop: 8 }}>{t("met.model_t", { v: mm.model_version, r: mm.resolution_used, t0: mm.train_years[0], t1: mm.train_years[1], issue: monthName(mm.issue_month) })}</div>}
          {mm && <div className="muted" style={{ marginTop: 6 }}>{t("met.class_rule")}: {mm.class_rule}</div>}
          {mm && <div className="muted">{t("met.drivers")}: {mm.drivers}</div>}
          <div className="muted" style={{ marginTop: 6 }}>{t("met.harm")}: {t("met.harm_t", { mape: num(metrics.mape_total_monthly_pct, 1), r2: num(metrics.r2_cell2_month, 2) })}</div>
          <div className="muted">{t("met.coverage")}: {m.coverage_2026}</div>
        </div>
      </div>
      <div className="stack" style={{ gap: 14 }}>
        {imp.length > 0 && <div className="pnl static" style={{ padding: 16 }} data-a><span className="lbl">{t("met.imp")}</span>
          <div className="fi" style={{ marginTop: 12 }}>{imp.map(([f, v]) => <div key={f} style={{ display: "contents" }}>
            <span>{t(`feat.${f}`)}</span><div className="b"><i style={{ "--w": `${(v / max) * 100}%` } as React.CSSProperties} /></div><span className="num muted">{num(v, 2)}</span></div>)}</div></div>}
        {m.ipp && <div className="pnl static" style={{ padding: 16 }} data-a><span className="lbl">{t("met.ipp")}</span>
          <div className="formula" style={{ marginTop: 10 }}>IPP = N<sup>{num(m.ipp.weights.n, 2)}</sup> · V<sup>{num(m.ipp.weights.v, 2)}</sup> · E<sup>{num(m.ipp.weights.e, 2)}</sup> &nbsp;∈ [{num(m.ipp.floor, 2)}; 1]</div>
          <div className="stack sub" style={{ gap: 6, marginTop: 10 }}>
            <div><b style={{ color: "var(--n)" }}>■</b> {t("met.ipp_n")}</div><div><b style={{ color: "var(--v)" }}>■</b> {t("met.ipp_v")}</div><div><b style={{ color: "var(--e)" }}>■</b> {t("met.ipp_e")}</div>
            {Object.entries(m.ipp.cuts).map(([h, c]) => <div key={h} className="muted">{t("met.cuts", { h, m: num(c.medio, 2), a: num(c.alto, 2), c: num(c.critico, 2) })}</div>)}
          </div></div>}
        <div className="pnl static" style={{ padding: 16 }} data-a><span className="lbl">{t("met.sources")}</span>
          <table className="t" style={{ marginTop: 6, fontSize: 11.5 }}><tbody>{m.sources.map((s) => <tr key={s.name}><td>{s.name}</td><td className="muted">{s.use}</td><td className="muted num">{s.accessed}</td></tr>)}</tbody></table></div>
      </div>
    </div>
  );
}
