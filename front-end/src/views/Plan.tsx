import { Fragment, useState } from "react";
import type { AppCtx } from "../App";
import { ApiError, streamPost } from "../api/client";
import type { PriorityItem } from "../api/dto";
import { decisionKey, forArea, useDecisions } from "../decisions";
import { getLang, monthName, num, t } from "../i18n";
import { nf } from "../geo";
import { Chip, Nve, useEntrance, weakHorizon } from "../ui";
import { Recs } from "./Recs";

export const unitName = (i: PriorityItem) => i.name ?? t(`kind.${i.kind}`, { id: i.id.slice(-6) });

function csv(items: PriorityItem[]) {
  const head = ["rank", "id", "name", "ipp", "ipp_level", "n", "v", "e", "forecast_level", "predicted", "critical_cells", "rules"];
  const rows = items.map((i, k) => [k + 1, i.id, unitName(i), i.ipp, i.level, i.n, i.v, i.e, i.forecast_level, i.predicted, i.critical_cells, i.recommendations.map((r) => r.rule_id).join(" ")]);
  const text = [head, ...rows].map((r) => r.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" })); a.download = "flaming-view-plano.csv"; a.click();
}

/** Tela 4 · Planejamento preventivo (RF-UI-05). */
export function Plan({ ctx }: { ctx: AppCtx }) {
  const { priorities: p, horizon, area } = ctx;
  const all = useDecisions();
  const [tab, setTab] = useState<"all" | "accepted" | "ignored">("all");
  const [open, setOpen] = useState<string | null>(null);
  const [ai, setAi] = useState<"idle" | "busy" | "ok" | "off">("idle");
  const [showLow, setShowLow] = useState(false);       // R5/R6 ocultas por padrão (U-02)
  const ref = useEntrance([area.id, horizon]);
  const mine = forArea(all, area.id, horizon);
  const recs = (i: PriorityItem) => showLow ? i.recommendations : i.recommendations.filter((r) => r.severity !== "low");
  const hiddenLow = showLow ? 0 : (p?.items ?? []).reduce((n, i) => n + i.recommendations.filter((r) => r.severity === "low").length, 0);
  const status = (i: PriorityItem) => recs(i).map((r) => all[decisionKey(area.id, horizon, i.id, r.rule_id)]?.status);
  const items = (p?.items ?? []).filter((i) => tab === "all" || status(i).includes(tab));
  const month = ctx.forecast?.horizons.find((x) => x.horizon === horizon)?.forecast_month;
  const month1 = ctx.forecast?.horizons.find((x) => x.horizon === 1)?.forecast_month;
  const reportUrl = `/report?area=${area.id}&horizon=${horizon}`;

  const generate = async () => {
    setAi("busy");
    let text = "";
    try {
      await streamPost("/assistant/report", { area_id: area.id, horizon, lang: getLang(),
        accepted: mine.filter((d) => d.status === "accepted"), ignored: mine.filter((d) => d.status === "ignored") }, (s) => { text += s; });
      sessionStorage.setItem(`fv.report.${area.id}.${horizon}.${getLang()}`, text); setAi("ok");
    } catch (e) { setAi(e instanceof ApiError ? "off" : "off"); }
  };

  return (
    <div ref={ref} className="page" style={{ background: "var(--bg)", zIndex: 8 }}>
      <div className="row between wrap">
        <div><div className="lbl" data-a>{t("plan.label")}</div>
          <div className="h1" data-a style={{ fontSize: 26 }}>{t("plan.title", { month: monthName(month) })}</div>
          <div className="sub" data-a style={{ maxWidth: 760 }}>{t("plan.sub", { area: area.name })}</div></div>
        <div className="row" data-a>
          <button className="btn" onClick={() => p && csv(p.items)} disabled={!p}>{t("plan.csv")}</button>
          <button className="btn" onClick={() => window.open(`${reportUrl}&print=1`, "_blank")}>{t("plan.pdf")}</button>
          <button className="btn pri" onClick={generate} disabled={ai === "busy"}>{t("plan.ai")}</button>
        </div>
      </div>
      {(ai === "ok" || ai === "off") && <div className={ai === "ok" ? "card" : "warnband"} role="status">{t(ai === "ok" ? "plan.report_ok" : "plan.report_off")}
        {" "}<a href="#/rep" style={{ color: "var(--accent)" }}>{t("nav.rep")}</a></div>}
      <div className="tabs" role="tablist" data-a>
        {(["all", "accepted", "ignored"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{t(`plan.tab.${k}`)}
            <span className="bd">{k === "all" ? p?.items.length ?? 0 : mine.filter((d) => d.status === k).length}</span></button>))}
      </div>
      <div data-a>
        <div className="warnband" role="note">{t("plan.rules_month", { month: monthName(month1) })}</div>
        {weakHorizon(ctx.method, horizon) && <div className="warnband" role="note">{t("hz.weak", { month: monthName(month) })}</div>}
      </div>
      <div className="row between wrap" data-a>
        <span className="row muted wrap">{t("plan.counts", { a: mine.filter((d) => d.status === "accepted").length, i: mine.filter((d) => d.status === "ignored").length })}
          · {showLow ? null : t("plan.lowhidden", { n: hiddenLow })}
          <button className="btn sm gh" aria-pressed={showLow} onClick={() => setShowLow(!showLow)}>{t(showLow ? "plan.hide" : "plan.show")}</button></span>
        <span className="row muted"><label className="row" style={{ gap: 6 }}>{t("plan.sort")}
          <select className="sel" value={ctx.sort} onChange={(e) => ctx.setSort(e.target.value as typeof ctx.sort)}>
            {(["action", "fire", "ipp"] as const).map((k) => <option key={k} value={k}>{t(`sort.${k}`)}</option>)}</select></label>
          {t("plan.sorted", { n: p?.total ?? 0, sort: t(`sort.${ctx.sort}`), h: horizon })}</span></div>
      <div className="pnl static" style={{ flex: 1, overflow: "auto" }} data-a>
        <table className="t">
          <thead><tr><th>{t("col.rank")}</th><th>{t("col.unit")}</th><th>{t("col.class")}</th><th className="r">{t("col.ipp")}</th><th>{t("col.nve")}</th>
            <th>{t("col.fire", { month: monthName(month, "short") })}</th><th className="r">{t("col.critical")}</th><th className="r">{t("col.pop")}</th><th className="r">{t("col.pred")}</th><th>{t("col.rules")}</th><th>{t("col.status")}</th><th>{t("col.action")}</th></tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={12} className="muted">{p ? t("plan.empty") : t("common.loading")}</td></tr>}
            {items.map((i) => {
              const st = status(i); const done = st.filter(Boolean).length;
              return <Fragment key={i.id}>
                <tr>
                  <td>{(p?.items.indexOf(i) ?? 0) + 1}</td>
                  <td><button className="btn sm gh" style={{ padding: 0, fontWeight: 600 }} aria-expanded={open === i.id} onClick={() => setOpen(open === i.id ? null : i.id)}>
                    {open === i.id ? "▾" : "▸"} {unitName(i)}</button>{i.ti_name && <div className="muted">{i.ti_name}</div>}</td>
                  <td title={i.capped ? t("ipp.capped") : undefined}><Chip level={i.level} kind="ipp" />{i.capped && <span className="muted"> ¹</span>}</td><td className="r"><b>{num(i.ipp, 2)}</b></td><td><Nve n={i.n} v={i.v} e={i.e} /></td>
                  <td><Chip level={i.forecast_level} /></td><td className="r">{i.critical_cells}</td><td className="r">{i.population == null ? "—" : nf(i.population)}</td><td className="r">{num(i.predicted, 1)}</td>
                  <td><span className="row" style={{ gap: 4 }}>{recs(i).map((r) => <span key={r.rule_id} className={`tag${r.severity === "high" ? " hi" : ""}`}>{r.rule_id}</span>)}</span></td>
                  <td className="muted">{recs(i).length === 0 ? "—" : done ? t("st.done", { a: done, t: st.length }) : t("st.pending")}</td>
                  <td><button className="btn sm" onClick={() => { i.kind === "municipality" ? ctx.goArea(i.id) : (ctx.flyTo(i.lat, i.lon, i.kind === "cell" ? 10 : 8), i.kind === "cell" && ctx.setCell(+i.id)); ctx.go(i.kind === "cell" ? "ter" : "map"); }}>{t("plan.locate")}</button></td>
                </tr>
                {open === i.id && <tr><td /><td colSpan={11}><Recs recs={recs(i)} area={area.id} horizon={horizon} unit={i.id} unitName={unitName(i)} /></td></tr>}
              </Fragment>;
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
