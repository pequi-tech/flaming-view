import { useState } from "react";
import type { Recommendation } from "../api/dto";
import { decide, decisionKey, useDecisions } from "../decisions";
import { getLang, t } from "../i18n";

/** Recomendações com Aceitar / Ignorar (motivo opcional), estado em localStorage (RF-UI-05). */
export function Recs({ recs, area, horizon, unit, unitName }: { recs: Recommendation[]; area: string; horizon: number; unit: string; unitName?: string | null }) {
  const all = useDecisions();
  const [reason, setReason] = useState<Record<string, string>>({});
  if (!recs.length) return <p className="muted">{t("ter.none")}</p>;
  return (
    <div className="stack" style={{ gap: 8 }}>
      {recs.map((r) => {
        const key = decisionKey(area, horizon, unit, r.rule_id);
        const d = all[key];
        const base = { area, horizon, unit, unitName, rule: r.rule_id, reason: reason[r.rule_id] };
        return (
          <div key={r.rule_id} className={`rec${r.severity === "high" ? " hi" : ""}${d?.status === "accepted" ? " ok" : d?.status === "ignored" ? " no" : ""}`}>
            <span />
            <div>
              <div className="t">{t(`rec.${r.rule_id}.t`)}</div>
              <div className="d">{t(`rec.${r.rule_id}.d`)}</div>
              <div className="m"><span className={`tag${r.severity === "high" ? " hi" : ""}`}>{r.rule_id} · {t(`sev.${r.severity}`)}</span>{r.decisions.join(" · ")}
                {d?.reason && <span>· “{d.reason}”</span>}</div>
            </div>
            <div className="a">
              {d ? <>
                <span className="st">{d.status === "accepted" ? t("rec.accepted", { d: new Date(d.at).toLocaleDateString(getLang(), { day: "2-digit", month: "short" }) }) : t("rec.ignored")}</span>
                <button className="btn sm gh" onClick={() => decide(null, key)}>{t("rec.undo")}</button>
              </> : <>
                <div className="row" style={{ gap: 6 }}>
                  <button className="btn sm pri" onClick={() => decide({ ...base, status: "accepted" }, key)}>{t("rec.accept")}</button>
                  <button className="btn sm" onClick={() => decide({ ...base, status: "ignored" }, key)}>{t("rec.ignore")}</button>
                </div>
                <input aria-label={t("rec.reason")} placeholder={t("rec.reason")} value={reason[r.rule_id] ?? ""} onChange={(e) => setReason({ ...reason, [r.rule_id]: e.target.value })} />
              </>}
            </div>
          </div>);
      })}
    </div>
  );
}
