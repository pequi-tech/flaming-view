import { useEffect, useState } from "react";
import type { AppCtx } from "../App";
import { ApiError, fvApi } from "../api/client";
import type { CellResponseDTO } from "../api/dto";
import { decisionKey, useDecisions } from "../decisions";
import { monthName, monthShort, num, t } from "../i18n";
import { Chip, CountUp, Explain, Meter, ordinal, useEntrance, useLenis } from "../ui";
import { Recs } from "./Recs";

/** Tela 3 · Análise do território (RF-UI-04): todos os números vêm de /cell/{id}. */
export function Territory({ ctx }: { ctx: AppCtx }) {
  const [c, setC] = useState<CellResponseDTO>();
  const [err, setErr] = useState<string>();
  const all = useDecisions();
  const ref = useEntrance([c?.cell_id]);
  const scroll = useLenis<HTMLDivElement>();
  useEffect(() => {
    if (ctx.cell === null) { setC(undefined); return; }
    const ab = new AbortController();
    setErr(undefined);
    fvApi.cell(ctx.cell, ab.signal).then(setC).catch((e) => !ab.signal.aborted && setErr(e instanceof ApiError && e.status === 404 ? t("map.nocell") : e.message));
    return () => ab.abort();
  }, [ctx.cell]);

  const h = ctx.horizon;
  const f = c?.forecast.find((x) => x.horizon === h);
  const accepted = c ? c.recommendations.filter((r) => all[decisionKey(ctx.area.id, h, String(c.cell_id), r.rule_id)]?.status === "accepted").length : 0;
  const place = c ? [c.place.municipality_name, c.place.country_name].filter(Boolean).join(" · ") : "";
  const years = c ? [...new Set(c.history.map((x) => x.year))] : [];
  return (
    <aside ref={ref} className="pnl drawer" style={{ width: 528 }} aria-label={t("nav.ter")}>
      <div style={{ padding: "16px 18px 12px", borderBottom: "1px solid var(--line)" }}>
        <div className="row between">
          <span className="lbl" data-a>{ctx.cell !== null ? t("ter.cell", { id: ctx.cell }) : t("nav.ter")}</span>
          <div className="row" style={{ gap: 6 }}>
            {c && <button className="btn sm gh" onClick={() => ctx.go("ia")}>{t("ter.ask")}</button>}
            <button className="btn sm" onClick={() => { ctx.setCell(null); if (location.hash === "#/ter") ctx.go("map"); }}>{t("ter.close")}</button>
          </div>
        </div>
        <div className="h1" data-a>{c ? place || "—" : ctx.cell === null ? t("map.label") : err ?? t("ter.loading")}</div>
        {c && <div className="sub" data-a>{t("ter.coords", { lat: num(c.lat + 0.025, 3), lon: num(c.lon + 0.025, 3) })} · {c.place.ti_name ? t("ter.ti", { name: c.place.ti_name }) : t("ter.noti")}</div>}
      </div>
      {c && f && <div ref={scroll} className="scroll" style={{ flex: 1 }}><div className="stack" style={{ padding: "14px 18px 18px", gap: 12 }}>
        <div className="row ter-cards" style={{ alignItems: "stretch", gap: 10 }} data-a>
          <div className="card spot" style={{ flex: 1.15 }}>
            <div className="row between"><span className="lbl">{t("ter.ipp", { h })}</span><Chip level={f.ipp.level} kind="ipp" /></div>
            <div className="row" style={{ margin: "10px 0 6px", gap: 12, alignItems: "flex-end" }}>
              <b style={{ font: "650 38px/1 var(--font)" }}><CountUp value={f.ipp.value} digits={2} /></b>
              <span className="muted" style={{ paddingBottom: 4 }}>IPP</span></div>
            <div className="sub"><Explain level={f.ipp.level} ex={f.ipp.explanation} /></div>
            <div className="stack" style={{ gap: 7, marginTop: 10 }}><Meter k="n" value={f.ipp.n} /><Meter k="v" value={f.ipp.v} /><Meter k="e" value={f.ipp.e} /></div>
          </div>
          <div className="card" style={{ flex: 1 }}>
            <span className="lbl">{t("ter.by_h")}</span>
            <table className="t" style={{ marginTop: 6, fontSize: 12 }}><tbody>{c.forecast.map((x) => (
              <tr key={x.horizon}><td style={{ padding: "7px 4px" }}>{monthName(x.forecast_month, "short")} · M+{x.horizon}</td>
                <td style={{ padding: "7px 4px" }}><Chip level={x.level} /></td>
                <td className="r" style={{ padding: "7px 4px" }}>{num(x.predicted, 1)} <span className="muted">{num(x.lo, 1)}–{num(x.hi, 1)}</span></td></tr>))}</tbody></table>
            <div className="muted" style={{ marginTop: 6 }}>{t("ter.unit")}</div>
          </div>
        </div>
        <div className="card" data-a>
          <div className="row between"><span className="lbl">{t("ter.hist")}</span><span className="muted">{t("ter.empty")}</span></div>
          <div className="heat" style={{ marginTop: 10 }} role="img" aria-label={t("ter.hist")}>
            {years.map((y) => <div key={y} style={{ display: "contents" }}><span className="y">{y}</span>
              {Array.from({ length: 12 }, (_, m) => { const e = c.history.find((x) => x.year === y && x.month === m + 1);
                return <i key={m} className={e && e.value > 0 ? `k${ordinal(e.level)}` : ""} title={e ? `${monthShort(m + 1)}/${y}: ${num(e.value, 1)} · ${t(`lvl.${e.level}`)}` : ""} />; })}</div>)}
            <div className="x">{Array.from({ length: 12 }, (_, m) => <span key={m}>{monthShort(m + 1).slice(0, 3)}</span>)}</div>
          </div>
        </div>
        <div data-a>
          <div className="row between"><span className="lbl">{t("ter.drivers")}</span></div>
          <div className="drv" style={{ marginTop: 8 }}>{c.drivers.map((d) => (
            <div key={d.key} className={`card${d.available ? "" : " na"}`}>
              <div className="row between muted"><span>{t(`drv.${d.key}`)}</span><span>{d.importance !== null ? t("drv.imp", { v: num(d.importance, 2) }) : ""}</span></div>
              <div className="v num">{!d.available || d.value === null ? "—" : d.unit === "ratio" ? `${d.value > 0 ? "+" : ""}${num(d.value * 100)} %` : `${d.value > 0 ? "+" : ""}${num(d.value, 1)} ${d.unit}`}</div>
              {d.months && <div className="muted">{d.months.replace("..", " a ")}</div>}
              {d.available ? <div className="imp"><i style={{ "--w": `${Math.min(100, (d.importance ?? 0) * 100)}%` } as React.CSSProperties} /></div> : <div className="muted">{t("drv.na")}</div>}
            </div>))}</div>
        </div>
        <div>
          <div className="row between"><span className="lbl">{t("ter.recs", { n: accepted, t: c.recommendations.length })}</span><span className="muted">{t("ter.recs_note")}</span></div>
          <div style={{ marginTop: 8 }}><Recs recs={c.recommendations} area={ctx.area.id} horizon={h} unit={String(c.cell_id)} unitName={place} /></div>
        </div>
      </div></div>}
    </aside>
  );
}
