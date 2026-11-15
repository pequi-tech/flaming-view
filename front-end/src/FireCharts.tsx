import type { CalendarResponseDTO, CalendarMonthDTO, SeriesResponseDTO } from "./api/dto";
import { nf } from "./geo";

const MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const LEVEL_COLOR: Record<CalendarMonthDTO["level"], string> = {
  baixo: "#60a5fa", normal: "#34d399", alto: "#fbbf24", critico: "#fb6542",
};

export function CalendarHeatmap({ data, year, month, onSelect }: {
  data: CalendarResponseDTO; year: number; month: number; onSelect: (year: number, month: number) => void;
}) {
  const years = [...new Set(data.months.map((entry) => entry.year))].sort((a, b) => b - a);
  const find = (y: number, m: number) => data.months.find((entry) => entry.year === y && entry.month === m);
  return (
    <div className="fire-calendar" role="grid" aria-label="Calendário de atividade mensal">
      <div className="fire-calendar-row fire-calendar-header" role="row">
        <span aria-hidden="true" />{MONTHS.map((label) => <span role="columnheader" key={label}>{label}</span>)}
      </div>
      {years.map((y) => (
        <div className="fire-calendar-row" role="row" key={y}>
          <span className="fire-calendar-year" role="rowheader">{y}</span>
          {MONTHS.map((label, i) => {
            const entry = find(y, i + 1);
            const active = y === year && i + 1 === month;
            return entry ? (
              <button key={label} type="button" role="gridcell" className={`fire-month${active ? " is-selected" : ""}`}
                style={{ "--month-color": LEVEL_COLOR[entry.level] } as React.CSSProperties}
                aria-label={`${label} ${y}: ${nf(entry.value)} ${data.unit}, nível ${entry.level}`}
                title={`${label}/${y} · ${nf(entry.value)} · mediana ${nf(entry.median)} · ${entry.level}`}
                onClick={() => onSelect(y, i + 1)} />
            ) : <span key={label} className="fire-month is-empty" />;
          })}
        </div>
      ))}
      <div className="fire-calendar-legend"><span><i className="legend-low" /> Baixa</span><span><i className="legend-mid" /> Típica</span><span><i className="legend-high" /> Alta</span><span><i className="legend-critical" /> Crítica</span></div>
    </div>
  );
}

export function SeriesChart({ data }: { data: SeriesResponseDTO }) {
  const points = data.years;
  if (!points.length) return <p className="gx-note">Sem observações no período.</p>;
  const width = 320, height = 112, inset = { left: 44, right: 8, top: 10, bottom: 22 };
  const plotWidth = width - inset.left - inset.right;
  const plotHeight = height - inset.top - inset.bottom;
  const max = Math.max(1, ...points.map((point) => point.hi));
  const x = (index: number) => inset.left + (points.length < 2 ? plotWidth / 2 : index * plotWidth / (points.length - 1));
  const y = (value: number) => inset.top + plotHeight * (1 - value / max);
  const line = points.map((point, i) => `${i ? "L" : "M"}${x(i)},${y(point.value)}`).join(" ");
  const band = `${points.map((point, i) => `${i ? "L" : "M"}${x(i)},${y(point.hi)}`).join(" ")} ${points.map((point, i) => `L${x(points.length - 1 - i)},${y(points[points.length - 1 - i].lo)}`).join(" ")} Z`;
  return (
    <div className="fire-chart-wrap">
      <svg className="fire-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Série anual com faixa de incerteza">
        {[0, 0.5, 1].map((fraction) => <line key={fraction} x1={inset.left} x2={width - inset.right} y1={inset.top + plotHeight * fraction} y2={inset.top + plotHeight * fraction} className="chart-grid" />)}
        <path d={band} className="chart-band" />
        <path d={line} className="chart-line" />
        {points.map((point, i) => <circle key={point.year} cx={x(i)} cy={y(point.value)} r="2.5" className="chart-dot"><title>{point.year}: {nf(point.value)}; faixa {nf(point.lo)}–{nf(point.hi)}</title></circle>)}
        <text x="1" y={inset.top + 3}>{nf(max)}</text>
        <text x="1" y={inset.top + plotHeight}>{nf(0)}</text>
        <text x={inset.left} y={height - 4}>{points[0].year}</text>
        <text x={width - inset.right} y={height - 4} textAnchor="end">{points.at(-1)?.year}</text>
      </svg>
      <div className="fire-chart-legend"><span><i className="chart-key-line" /> Atividade anual</span><span><i className="chart-key-band" /> Faixa de incerteza</span></div>
      <p className="gx-note">Unidade: {data.unit}</p>
    </div>
  );
}

export function SeasonChart({ data }: { data: CalendarResponseDTO }) {
  const months = MONTHS.map((name, index) => ({
    name,
    median: data.months.find((entry) => entry.month === index + 1)?.median ?? 0,
  }));
  const max = Math.max(1, ...months.map((entry) => entry.median));
  const peaks = [...months].sort((a, b) => b.median - a.median).slice(0, 3);
  const hasActivity = months.some((entry) => entry.median > 0);
  const medianYear = months.reduce((sum, entry) => sum + entry.median, 0);
  return (
    <div>
      <div className="season-bars" aria-label="Mediana histórica por mês">
        {months.map((entry) => <div key={entry.name} className="season-bar-col" title={`${entry.name}: mediana ${nf(entry.median)}; ${(medianYear ? (entry.median / medianYear) * 100 : 0).toFixed(1)}% do perfil mediano anual`}>
          <span className="season-bar-track"><i style={{ height: `${Math.max(entry.median > 0 ? 5 : 0, (entry.median / max) * 100)}%` }} /></span>
          <small>{entry.name.slice(0, 1)}</small>
        </div>)}
      </div>
      <p className="gx-note">{hasActivity ? `Meses de maior mediana: ${peaks.filter((entry) => entry.median > 0).map((entry) => `${entry.name} (${medianYear ? ((entry.median / medianYear) * 100).toFixed(0) : 0}%)`).join(", ")}.` : "Sem atividade mediana no histórico desta área."} Perfil derivado do calendário histórico.</p>
    </div>
  );
}
