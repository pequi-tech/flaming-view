import type { BackendStatus, MethodStatus } from "./api/useFireData";

const METRICS: Array<[string, string, (value: number) => string]> = [
  ["mape_total_monthly_pct", "MAPE mensal", (value) => `${value.toFixed(1)}%`],
  ["r2_cell2_month", "R² célula/mês", (value) => value.toFixed(2)],
  ["mdape_cell2_month_pct", "Erro mediano", (value) => `${value.toFixed(1)}%`],
  ["aqua_snpp_global_median", "Fator Aqua → VIIRS", (value) => value.toFixed(3)],
  ["n20_snpp_global_median", "Fator NOAA-20 → VIIRS", (value) => value.toFixed(3)],
];

export function MethodPanel({ backend, method }: { backend: BackendStatus; method: MethodStatus }) {
  if (method.status === "loading") return <p className="gx-note">Carregando transparência dos dados…</p>;
  if (method.status === "error") return <p className="fire-feedback is-error">{method.message}</p>;

  const data = method.data;
  const metrics = data.metrics;
  const value = (key: string) => typeof metrics[key] === "number" ? metrics[key] as number : undefined;
  const calibration = Array.isArray(metrics.calibration_years) ? metrics.calibration_years as number[] : [];
  const holdout = Array.isArray(metrics.holdout_years) ? metrics.holdout_years as number[] : [];
  const uncertainty = Array.isArray(metrics.q10_q90_pred_over_actual) ? metrics.q10_q90_pred_over_actual as number[] : [];
  const levelShare = metrics.level_share && typeof metrics.level_share === "object" ? metrics.level_share as Record<string, unknown> : {};
  return (
    <div className="method-content">
      <div className="method-health"><i className={backend.status === "online" ? "is-online" : "is-offline"} />
        {backend.status === "online" ? "API conectada" : backend.status === "error" ? "API indisponível" : "Conectando à API"}
        <span>· release {data.release}</span>
      </div>
      <dl className="method-meta">
        <dt>Dados</dt><dd>{data.years[0]}–{data.years.at(-1)} · {data.unit}</dd>
        <dt>Registros</dt><dd>{data.rows.toLocaleString("pt-BR")}</dd>
        <dt>Contrato</dt><dd>v{data.contract_version}</dd>
        <dt>Tempo real</dt><dd>{backend.status === "online" && backend.health.realtime ? "FIRMS NRT ativo" : "Chave FIRMS não configurada"}</dd>
      </dl>
      <div className="method-metrics">
        {METRICS.map(([key, label, format]) => {
          const metric = value(key);
          return metric === undefined ? null : <div key={key}><span>{label}</span><b>{format(metric)}</b></div>;
        })}
        {uncertainty.length === 2 && <div><span>Faixa p10–p90</span><b>{uncertainty[0].toFixed(2)}–{uncertainty[1].toFixed(2)}×</b></div>}
        {typeof levelShare.c2 === "number" && <div><span>Fator local c2</span><b>{(levelShare.c2 * 100).toFixed(1)}%</b></div>}
      </div>
      {(calibration.length > 0 || holdout.length > 0) && <p className="gx-note">
        Calibração {calibration.join("–") || "—"} · validação independente {holdout.join(", ") || "—"}.
      </p>}
      <p className="gx-note">Série harmonizada por sensor: AQUA (2003–2011), VIIRS S-NPP (2012–2025), NOAA-20 (2026+).</p>
    </div>
  );
}
