import { useEffect, useLayoutEffect, useRef } from "react";
import gsap from "gsap";
import Lenis from "lenis";
import { num, t } from "./i18n";

export const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const ORD: Record<string, number> = { baixo: 0, normal: 1, medio: 1, alto: 2, critico: 3 };
export const ordinal = (level: string | null | undefined) => (level ? ORD[level] ?? -1 : -1);

/** Classe com cor e rótulo (nunca só cor). kind=ipp = Prioridade (azul-acinzentado); lvl = Fogo previsto (laranja). */
export function Chip({ level, kind = "lvl" }: { level: string | null | undefined; kind?: "lvl" | "ipp" }) {
  if (!level) return <span className="chip k-1"><i />—</span>;
  return <span className={`chip k${ordinal(level)}${kind === "ipp" ? " ipp" : ""}`}><i />{t(`${kind}.${level}`)}</span>;
}

/** Número que conta até o valor (CountUp do React Bits, com GSAP). Respeita prefers-reduced-motion. */
export function CountUp({ value, digits = 0, suffix = "" }: { value: number | null | undefined; digits?: number; suffix?: string }) {
  const el = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const node = el.current;
    if (!node) return;
    if (value === null || value === undefined || !Number.isFinite(value)) { node.textContent = "—"; return; }
    node.textContent = num(value, digits) + suffix;              // valor final já visível; a contagem só anima por cima
    if (reduced() || document.hidden) return;
    const o = { v: 0 };
    const tw = gsap.to(o, { v: value, duration: 1.2, ease: "power2.out", onUpdate: () => { node.textContent = num(o.v, digits) + suffix; } });
    return () => { tw.kill(); node.textContent = num(value, digits) + suffix; };
  }, [value, digits, suffix]);
  return <span ref={el} className="num" />;
}

/** Medidor em arco: fração 0..1 do arco, cor pela classe. */
export function Arc({ frac, level, big, caption, small }: { frac: number; level?: string; big: React.ReactNode; caption: string; small?: boolean }) {
  const f = Math.max(0, Math.min(1, frac));
  const col = level ? `var(--c${Math.max(0, ordinal(level))})` : "var(--accent)";
  const len = Math.PI * 90;
  return (
    <div className={`arc${small ? " sm" : ""}`} role="img" aria-label={`${caption}`}>
      <svg viewBox="0 0 220 124" aria-hidden>
        <path d="M20 115 A90 90 0 0 1 200 115" fill="none" stroke="rgba(148,178,220,.12)" strokeWidth="14" strokeLinecap="round" />
        <path d="M20 115 A90 90 0 0 1 200 115" fill="none" stroke={col} strokeWidth="14" strokeLinecap="round"
          strokeDasharray={`${len * f} ${len}`} style={{ transition: "stroke-dasharray 1.2s cubic-bezier(.2,.8,.2,1)" }} />
      </svg>
      <div className="val"><b>{big}</b><small>{caption}</small></div>
    </div>
  );
}

export function Meter({ k, value }: { k: "n" | "v" | "e"; value: number }) {
  return <div className={`meter ${k}`}><b>{k.toUpperCase()}</b><div className="bar"><i style={{ "--w": `${Math.round(value * 100)}%` } as React.CSSProperties} /></div>
    <span className="vl">{num(value, 2)}</span></div>;
}

export const Nve = ({ n, v, e }: { n: number; v: number; e: number }) => (
  <span className="nve" aria-label={`N ${num(n, 2)} · V ${num(v, 2)} · E ${num(e, 2)}`}>
    <i style={{ width: `${n * 33}%`, background: "var(--n)" }} /><i style={{ width: `${v * 33}%`, background: "var(--v)" }} /><i style={{ width: `${e * 33}%`, background: "var(--e)" }} />
  </span>
);

/** Entrada da tela: itens [data-a] sobem em sequência (timeline GSAP, 40 ms entre itens). */
export function useEntrance(deps: unknown[]) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!ref.current || reduced()) return;
    const ctx = gsap.context(() => {
      gsap.from("[data-a]", { y: 12, opacity: 0, duration: 0.6, ease: "power3.out", stagger: 0.04, clearProps: "transform,opacity" });   // "all" apagaria o padding inline dos cartões
    }, ref);
    return () => ctx.revert();
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return ref;
}

/** Rolagem suave (Lenis) num contêiner com .scroll. */
export function useLenis<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (!ref.current || reduced()) return;
    const content = ref.current.firstElementChild as HTMLElement | null;
    if (!content) return;
    const lenis = new Lenis({ wrapper: ref.current, content, smoothWheel: true });
    let id = 0;
    const raf = (time: number) => { lenis.raf(time); id = requestAnimationFrame(raf); };
    id = requestAnimationFrame(raf);
    return () => { cancelAnimationFrame(id); lenis.destroy(); };
  }, []);
  return ref;
}

/** Luz que segue o cursor nos cartões .spot (SpotlightCard do React Bits), um único listener. */
export function installSpotlight() {
  window.addEventListener("pointermove", (e) => {
    const el = (e.target as HTMLElement | null)?.closest?.(".spot") as HTMLElement | null;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`); el.style.setProperty("--my", `${e.clientY - r.top}px`);
  }, { passive: true });
}

export function Explain({ level, ex, kind = "ipp" }: { level: string; ex: { dominant: string[]; weak: string }; kind?: string }) {
  return <>{t("explain", { level: t(`${kind}.${level}`), a: t(`comp.${ex.dominant[0]}`), b: t(`comp.${ex.dominant[1]}`), c: t(`comp.${ex.weak}`) })}</>;
}

const P = { fill: "none", stroke: "currentColor", strokeWidth: 1.7 };
export const ICONS: Record<string, React.ReactNode> = {
  sit: <svg viewBox="0 0 24 24" {...P}><path d="M3 12h4l3 7 4-14 3 7h4" /></svg>,
  map: <svg viewBox="0 0 24 24" {...P}><path d="m9 4-6 2v14l6-2 6 2 6-2V4l-6 2-6-2Zm0 0v14m6-12v14" /></svg>,
  ter: <svg viewBox="0 0 24 24" {...P}><circle cx="12" cy="11" r="3" /><path d="M12 21s7-6.2 7-11a7 7 0 0 0-14 0c0 4.8 7 11 7 11Z" /></svg>,
  plan: <svg viewBox="0 0 24 24" {...P}><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" /></svg>,
  rep: <svg viewBox="0 0 24 24" {...P}><path d="M7 3h7l5 5v13H7z M14 3v5h5M10 13h6M10 17h6" /></svg>,
  ia: <svg viewBox="0 0 24 24" {...P}><path d="M12 3l1.8 4.6L18 9l-4.2 1.4L12 15l-1.8-4.6L6 9l4.2-1.4zM18 15l.9 2.1L21 18l-2.1.9L18 21l-.9-2.1L15 18l2.1-.9z" /></svg>,
  met: <svg viewBox="0 0 24 24" {...P}><circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v5h1" /></svg>,
};

/** Horizonte sem ganho sobre a climatologia (MAE pior que a média histórica): a tela avisa "só tendência" (U-08). */
export const weakHorizon = (method: { model: { horizons: Record<string, { gain: number | null }> } | null } | undefined, h: number) =>
  (method?.model?.horizons[String(h)]?.gain ?? 0) < 0;
