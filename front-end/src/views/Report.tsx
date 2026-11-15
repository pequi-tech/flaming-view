import { useEffect, useState } from "react";
import type { AppCtx } from "../App";
import { fvApi } from "../api/client";
import type { ForecastResponseDTO, MethodV2, PrioritiesResponseDTO } from "../api/dto";
import { forArea, useDecisions } from "../decisions";
import { getLang, monthName, num, t, useLang } from "../i18n";
import { Chip } from "../ui";
import { unitName } from "./Plan";

/** Relatório A4 (RF-UI-06): rota /report?area=&horizon=[&print=1] ou aba Relatório. Impressão pelo navegador. */
export function ReportDoc({ areaId, horizon, autoPrint }: { areaId: string; horizon: number; autoPrint?: boolean }) {
  useLang();
  const [f, setF] = useState<ForecastResponseDTO>();
  const [p, setP] = useState<PrioritiesResponseDTO>();
  const [m, setM] = useState<MethodV2>();
  const all = useDecisions();
  useEffect(() => {
    Promise.all([fvApi.forecast({ area_id: areaId }), fvApi.priorities({ area_id: areaId, horizon, limit: 12 }), fvApi.method()])
      .then(([a, b, c]) => { setF(a); setP(b); setM(c); });
  }, [areaId, horizon]);
  useEffect(() => { if (autoPrint && f && p && m) setTimeout(() => window.print(), 400); }, [autoPrint, f, p, m]);
  const h = f?.horizons.find((x) => x.horizon === horizon);
  const llm = sessionStorage.getItem(`fv.report.${areaId}.${horizon}.${getLang()}`);
  const acts = forArea(all, areaId, horizon);
  const drivers = m?.model?.horizons["1"];
  return (
    <div className="a4wrap">
      <div className="row noprint"><button className="btn pri" onClick={() => window.print()}>{t("rep.print")}</button></div>
      <article className="a4">
        <div className="band"><div><small>{t("rep.kicker")}</small><h1>{t("rep.title", { area: f?.area.name ?? "…", month: monthName(h?.forecast_month) })}</h1></div>
          <div style={{ textAlign: "right", fontSize: 10, color: "#9fb6da" }}>Flaming View<br />{t("gov.disclaimer")}</div></div>
        <div className="body">
          <div className="id">
            <div><small>{t("rep.area")}</small>{f?.area.name} ({f?.area.id})</div><div><small>{t("rep.period")}</small>{monthName(h?.forecast_month, "short")} · M+{horizon}</div>
            <div><small>{t("rep.generated")}</small>{new Date().toLocaleString(getLang(), { dateStyle: "short", timeStyle: "short" })}</div>
            <div><small>{t("rep.version")}</small>{f?.model_version} · {f?.release.slice(0, 8)}</div></div>
          <h2>{t("rep.s1")}</h2>
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{llm ?? (h ? t("rep.template", { month: monthName(h.forecast_month), area: f!.area.name, level: t(`lvl.${h.level}`).toLowerCase(),
            ratio: h.ratio === null ? "—" : `${num(h.ratio, 2)}×`, crit: h.classes.critico }) : "…")}</p>
          <p className="muted" style={{ color: "#6b7280", fontSize: 9.5 }}>{llm ? t("rep.llm_note") : t("rep.tpl_note")}</p>
          <h2>{t("rep.s2")}</h2>
          <p className="note" style={{ margin: "0 0 6px" }}>{t("plan.rules_month", { month: monthName(f?.horizons.find((x) => x.horizon === 1)?.forecast_month) })}</p>
          <table><thead><tr><th>#</th><th>{t("col.unit")}</th><th>{t("col.class")}</th><th>{t("col.ipp")}</th><th>{t("col.nve")}</th><th>{t("col.critical")}</th><th>{t("col.rules")}</th></tr></thead>
            <tbody>{p?.items.map((i, k) => <tr key={i.id}><td>{k + 1}</td><td>{unitName(i)}</td><td><Chip level={i.level} kind="ipp" /></td><td>{num(i.ipp, 2)}</td>
              <td>{num(i.n, 2)} · {num(i.v, 2)} · {num(i.e, 2)}</td><td>{i.critical_cells}</td><td>{i.recommendations.map((r) => r.rule_id).join(" ")}</td></tr>)}</tbody></table>
          <h2>{t("rep.s3")}</h2>
          {acts.length === 0 ? <p className="note">{t("rep.noactions")}</p> :
            <table><thead><tr><th>{t("rep.situation")}</th><th>{t("rep.action")}</th><th>{t("rep.rule")}</th><th>{t("rep.units")}</th><th>{t("rep.reason")}</th></tr></thead>
              <tbody>{acts.map((d) => <tr key={`${d.unit}${d.rule}`}><td>{d.status === "accepted" ? t("rec.accepted", { d: "" }) : t("rec.ignored")}</td>
                <td>{t(`rec.${d.rule}.t`)}</td><td>{d.rule}</td><td>{d.unitName ?? d.unit}</td><td>{d.reason ?? ""}</td></tr>)}</tbody></table>}
          <h2>{t("rep.s4")}</h2>
          <p style={{ margin: 0 }}>{drivers ? drivers.features.map((ft, i) => [ft, drivers.importances[i]] as const).sort((a, b) => b[1] - a[1]).slice(0, 5)
            .map(([ft, v]) => `${t(`feat.${ft}`)} (${num(v, 2)})`).join(" · ") : "—"} · AUC M+{horizon} {num(h?.metrics.auc, 2)}</p>
          <h2>{t("rep.s5")}</h2>
          <p className="note" style={{ margin: 0 }}>{t("met.not_t")} {!f?.recent_data && t("sit.stale", { month: monthName(f?.issue_month) })}</p>
          <div className="sig"><div>{t("rep.sig1")}</div><div>{t("rep.sig2")}</div></div>
        </div>
        <div className="foot"><span>{t("rep.s6")}: {m?.sources.map((s) => s.name.split(" · ")[0]).join(" · ")}</span><span>Flaming View</span></div>
      </article>
    </div>
  );
}

export const Report = ({ ctx }: { ctx: AppCtx }) => <div style={{ position: "absolute", inset: 0, background: "var(--page)", zIndex: 8 }}><ReportDoc areaId={ctx.area.id} horizon={ctx.horizon} /></div>;
