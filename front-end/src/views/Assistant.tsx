import { useEffect, useRef, useState } from "react";
import type { AppCtx } from "../App";
import { ApiError, streamPost } from "../api/client";
import { getLang, num, t } from "../i18n";
import { Chip, useLenis } from "../ui";

type Msg = { role: "user" | "assistant"; content: string };

/** Assistente ancorado (RF-UI-07): contexto visível, sugestões, resposta em streaming com aria-live. */
export function Assistant({ ctx }: { ctx: AppCtx }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  // motivo da indisponibilidade; guardado na sessão para a gaveta já abrir desabilitada (U-06)
  const [off, setOffState] = useState<string | null>(() => sessionStorage.getItem("fv.ia.off"));
  const setOff = (v: string) => { sessionStorage.setItem("fv.ia.off", v); setOffState(v); };
  const [useCell, setUseCell] = useState(ctx.cell !== null);
  const scroll = useLenis<HTMLDivElement>();
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [msgs]);
  const h = ctx.forecast?.horizons.find((x) => x.horizon === ctx.horizon);

  const ask = async (text: string) => {
    if (!text.trim() || busy) return;
    const history: Msg[] = [...msgs, { role: "user", content: text }];
    setMsgs([...history, { role: "assistant", content: "" }]); setQ(""); setBusy(true);
    try {
      await streamPost("/assistant", { messages: history, area_id: ctx.area.level === "bbox" ? undefined : ctx.area.id,
        cell_id: useCell ? ctx.cell ?? undefined : undefined, horizon: ctx.horizon, lang: getLang() },
        (s) => setMsgs((m) => [...m.slice(0, -1), { role: "assistant", content: m[m.length - 1].content + s }]));
    } catch (e) {
      if (e instanceof ApiError && (e.code === "assistant_unavailable" || e.status === 503)) setOff(e.message);
      setMsgs((m) => m.slice(0, -1));
    } finally { setBusy(false); }
  };

  return (
    <aside className="pnl drawer" style={{ width: 460 }} aria-label={t("ia.label")}>
      <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--line)" }}>
        <div className="row between"><span className="lbl">{t("ia.label")}</span><span className="row muted" style={{ gap: 6 }}><span className={`dot${off || busy ? " off" : ""}`} />{off ? t("ia.off") : busy ? t("ia.busy") : t("ia.ready")}</span></div>
        <div className="h1" style={{ fontSize: 18 }}>{t("ia.title")}</div>
        <div className="row wrap" style={{ gap: 6, marginTop: 10 }}>
          <span className="chip k-1">{ctx.area.name}</span>
          {useCell && ctx.cell !== null && <span className="chip k-1">{t("ia.cellctx", { id: ctx.cell })}</span>}
          <span className="chip k-1">M+{ctx.horizon}</span>
          {h && <Chip level={h.level} />}
        </div>
      </div>
      <div ref={scroll} className="scroll" style={{ flex: 1 }}>
        <div className="stack" style={{ padding: "16px 18px", gap: 12 }} aria-live="polite" aria-busy={busy}>
          {off && <div className="warnband" role="status">{t(`ia.off.${["no_key", "billing", "auth"].includes(off) ? off : "upstream"}`)}
            <div className="muted" style={{ marginTop: 4 }}>{t("ia.code", { c: off })}</div></div>}
          {msgs.map((m, i) => <div key={i} className={`msg ${m.role === "user" ? "u" : "a"}`}>{m.content}{busy && i === msgs.length - 1 && <span className="caret" />}</div>)}
          <div ref={end} />
        </div>
      </div>
      <div className="stack" style={{ padding: "12px 18px 16px", borderTop: "1px solid var(--line)" }}>
        <div className="row wrap" style={{ gap: 6 }}>{["ia.s1", "ia.s2", "ia.s3"].map((k) => <button key={k} className="btn sm" disabled={busy || !!off} onClick={() => ask(t(k))}>{t(k)}</button>)}</div>
        <form className="inp" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("ia.input")} aria-label={t("ia.input")} disabled={!!off} />
          <button className="btn sm pri" type="submit" disabled={busy || !!off || !q.trim()} aria-label={t("ia.send")}>➤</button>
        </form>
        <div className="row between">
          <button className="btn sm gh" aria-pressed={useCell} disabled={ctx.cell === null} onClick={() => setUseCell(!useCell)}>{useCell ? "✓ " : ""}{t("ia.usecell")}</button>
          <span className="muted">{t("ia.note")}</span>
        </div>
      </div>
    </aside>
  );
}
