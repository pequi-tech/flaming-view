import type { AppCtx } from "../App";
import { monthName, num, pct, t } from "../i18n";
import { Arc, Chip, CountUp, Nve, useEntrance, useLenis, weakHorizon } from "../ui";

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** Tela 1 · Visão geral da área ativa (RF-UI-03). */
export function Situation({ ctx }: { ctx: AppCtx }) {
  const { forecast: f, priorities: p, horizon } = ctx;
  const h = f?.horizons.find((x) => x.horizon === horizon);
  const ref = useEntrance([f?.area.id, horizon]);
  const list = useLenis<HTMLDivElement>();
  const yoy = h && h.last_year ? h.predicted / h.last_year - 1 : null;
  const unitName = (i: NonNullable<typeof p>["items"][number]) => i.name ?? t(`kind.${i.kind}`, { id: i.id.slice(-6) });
  return (
    <aside ref={ref} className="pnl sit-panel" style={{ left: 12, top: 12, bottom: 12, width: 328, display: "flex", flexDirection: "column" }} aria-label={t("nav.sit")}>
      <div style={{ padding: "16px 16px 10px" }}>
        <div className="lbl" data-a>{t("sit.label", { area: f?.area.name ?? "…" })}</div>
        <div className="h1" data-a>{cap(monthName(h?.forecast_month))}</div>
        <div className="sub" data-a>{t("sit.sub")}</div>
      </div>
      {f && !f.recent_data && <div className="warnband" data-a style={{ margin: "0 16px 8px" }} role="status">{t("sit.stale", { month: monthName(f.issue_month) })}</div>}
      {weakHorizon(ctx.method, horizon) && <div className="warnband" data-a style={{ margin: "0 16px 8px" }} role="status">{t("hz.weak", { month: monthName(h?.forecast_month) })}</div>}
      <div style={{ padding: "0 16px" }} data-a>
        <Arc frac={Math.min(1, (h?.ratio ?? 0) / 3)} level={h?.level} caption={`${t("sit.gauge")} · ${h ? t(`lvl.${h.level}`) : "—"}`}
          big={<><CountUp value={h?.ratio ?? null} digits={2} />×</>} />
      </div>
      <div className="row between" style={{ padding: "6px 16px 0" }} data-a aria-live="polite">
        <span className="muted">{t("sit.current")}</span>
        {ctx.current ? <span className="row" style={{ gap: 6 }}><Chip level={ctx.current.level} /><b className="num">{ctx.current.ratio === null ? "—" : `${num(ctx.current.ratio, 2)}×`}</b></span>
          : <span className="muted">{ctx.current === null ? t("sit.current_off") : t("common.loading")}</span>}
      </div>
      <div className="kpis" style={{ padding: "10px 16px 0" }} data-a>
        <div className="kpi"><div className="lbl">{t("sit.critical")}</div><div className="v"><CountUp value={h?.classes.critico} /></div><div className="d">{t("sit.critical_d")}</div></div>
        <div className="kpi"><div className="lbl">{t("sit.high")}</div><div className="v"><CountUp value={h?.classes.alto} /></div><div className="d">{t("sit.high_d")}</div></div>
        <div className="kpi"><div className="lbl">{t("sit.yoy")}</div><div className="v num">{yoy === null ? "—" : `${yoy > 0 ? "+" : ""}${pct(yoy)}`}</div><div className="d">{t("sit.yoy_d")}</div></div>
      </div>
      <div style={{ padding: "12px 16px 0" }} data-a>
        <div className="lbl" style={{ marginBottom: 6 }}>{t("sit.horizons")}</div>
        <div className="hz">{f?.horizons.map((x) => (
          <div key={x.horizon} className={`card${x.horizon === horizon ? " on" : ""}`}>
            <div className="muted">M+{x.horizon} · {monthName(x.forecast_month, "short")}</div>
            <div style={{ margin: "5px 0" }}><Chip level={x.level} /></div>
            <div className="muted" style={{ fontSize: 10.5 }}>{weakHorizon(ctx.method, x.horizon) ? t("chip.trend")
              : t("chip.metric", { x: num((x.metrics.top10_precision ?? 0) / (x.metrics.base_rate || 1), 1) })}</div>
          </div>))}</div>
      </div>
      <div className="row between" style={{ padding: "14px 16px 6px" }}><span className="lbl">{t("sit.priority")}</span><span className="muted">{t("sit.priority_rank")}</span></div>
      <div ref={list} className="scroll" style={{ flex: 1, padding: "0 16px 14px" }}>
        <ol className="plist">{p?.items.slice(0, 12).map((i, k) => (
          <li key={i.id}><button className={`pi${k === 0 ? " first" : ""}`} style={{ width: "100%" }}
            onClick={() => i.kind === "municipality" ? ctx.goArea(i.id) : (ctx.flyTo(i.lat, i.lon, i.kind === "cell" ? 10 : 8), i.kind === "cell" && ctx.setCell(+i.id))}>
            <span className="rk">{k + 1}</span>
            <span><div className="nm">{unitName(i)}</div><div className="mt">{t("col.class")} {t(`ipp.${i.level}`).toLowerCase()} · {i.critical_cells} {t("sit.critical").toLowerCase()}{i.ti_name ? ` · ${i.ti_name}` : ""}</div><Nve n={i.n} v={i.v} e={i.e} /></span>
            <span className="ipp"><b className="num">{num(i.ipp, 2)}</b></span>
          </button></li>))}</ol>
      </div>
    </aside>
  );
}
