import type { BBox } from "../geo";

export type ApiErrorDTO = {
  code: string;
  message: string;
  details?: Array<{ field: string; message: string }>;
};

export type ErrorResponseDTO = { error: ApiErrorDTO };
export type Level = "baixo" | "normal" | "alto" | "critico";

export type HealthResponseDTO = {
  status: "ok";
  release: string;
  years: [number, number] | number[];
  realtime: boolean;
};

export type MethodResponseDTO = {
  release: string;
  contract_version: string;
  years: number[];
  rows: number;
  unit: string;
  metrics: Record<string, unknown>;
  quality: Record<string, unknown>;
};

export type CalendarQueryDTO = { bbox: BBox; from_year?: number; to_year?: number };
export type SeriesQueryDTO = CalendarQueryDTO;
export type CurrentQueryDTO = { bbox: BBox };
export type CellsQueryDTO = { year: number; month: number; res?: 0.25 | 0.5 | 1 | 2; bbox?: BBox };

export type CalendarMonthDTO = {
  year: number; month: number; value: number; lo: number; hi: number;
  median: number; p75: number; p90: number; ratio: number | null;
  level: Level; source: string | null; estimated: boolean;
};

export type CalendarResponseDTO = {
  area: string; unit: string; release: string; baseline_years: number[]; months: CalendarMonthDTO[];
};

export type YearTotalDTO = { year: number; value: number; lo: number; hi: number; source: string | null };
export type SeriesResponseDTO = { area: string; unit: string; release: string; years: YearTotalDTO[] };
export type CellDTO = { lat: number; lon: number; value: number };
export type CellsResponseDTO = {
  year: number; month: number; res: number; unit: string; release: string; cells: CellDTO[];
};

export type CurrentResponseDTO = {
  area: string; unit: string; year: number; month: number; day: number; days_in_month: number;
  value_to_date: number; projected: number; median: number; p75: number; p90: number;
  ratio: number | null; level: Level; source: "nrt"; satellite: string; stale: boolean;
};

// ---- contrato 1.1: previsão, território, áreas, assistente ----
export type IppLevel = "baixo" | "medio" | "alto" | "critico";
export type AreaRef = { id: string; name: string; level: string };
export type HorizonMetrics = { auc: number | null; top10_precision: number | null; base_rate: number | null; gain: number | null; mae: number | null; mae_baseline: number | null; resolution_used: number | null };
export type HorizonDTO = {
  horizon: number; forecast_month: string | null; classes: Record<Level, number>; cells: number;
  predicted: number; lo: number; hi: number; median: number; p75: number; p90: number; ratio: number | null;
  level: Level; last_year: number | null; metrics: HorizonMetrics;
};
export type ForecastResponseDTO = {
  area: AreaRef; unit: string; release: string; model_version: string | null; issue_month: string | null;
  recent_data: boolean; horizons: HorizonDTO[]; lineage: AreaRef[];
};
export type Recommendation = { rule_id: string; decisions: string[]; severity: "high" | "medium" | "low"; key: string };
export type Explanation = { dominant: ("n" | "v" | "e")[]; weak: "n" | "v" | "e" };
export type IppDTO = { value: number; level: IppLevel; n: number; v: number; e: number; explanation: Explanation };
export type PriorityItem = IppDTO & {
  id: string; kind: "municipality" | "cell" | "hexagon"; name: string | null; ipp: number; forecast_level: Level;
  predicted: number; cells: number; critical_cells: number; ti_name: string | null; lat: number; lon: number;
  recommendations: Recommendation[];
};
export type PrioritiesResponseDTO = { area: AreaRef; horizon: number; granularity: string; sort: string; total: number; release: string; cuts: Record<string, number>; items: PriorityItem[] };
export type CellForecast = { horizon: number; forecast_month: string; level: Level; predicted: number; lo: number; hi: number; ratio: number; ipp: IppDTO };
export type Driver = { key: string; value: number | null; unit: string; importance: number | null; available: boolean };
export type CellResponseDTO = {
  cell_id: number; lat: number; lon: number; release: string; model_version: string; recent_data: boolean; issue_month: string;
  place: { country: string; country_name?: string; state_id?: string; state_name?: string; municipality_id?: string; municipality_name?: string; ti_name: string | null };
  exposure: { v: number; e: number; e_pop: number; e_ti: number };
  forecast: CellForecast[];
  history: { year: number; month: number; value: number; level: Level; median: number }[];
  climatology: { month: number; p25: number; median: number; p75: number; p90: number }[];
  drivers: Driver[]; recommendations: Recommendation[];
};
export type AreaHit = { area_id: string; level: "country" | "state" | "municipality"; name: string; parent_id: string | null };
export type LayerCell = { id: string | null; lat: number; lon: number; value: number; level: string | null };
export type LayerResponseDTO = { layer: string; horizon: number | null; shape: string; h3_res: number | null; unit: string; cuts: Record<string, number> | null; cells: LayerCell[] };
export type ModelMetrics = {
  model_version: string; resolution_used: number; train_years: number[]; test_years: number[]; issue_month: string;
  class_rule: string; drivers: string; oni_recent?: number;
  horizons: Record<string, HorizonMetrics & { features: string[]; importances: number[]; n_train: number; n_test: number }>;
};
export type MethodV2 = MethodResponseDTO & {
  model: ModelMetrics | null;
  ipp: { weights: Record<string, number>; floor: number; cut_quantiles: Record<string, number>; cuts: Record<string, Record<string, number>> } | null;
  rules: Record<string, { decisions: string[]; severity: string }> | null;
  sources: { name: string; use: string; accessed: string }[]; partial_years: Record<string, unknown>; coverage_2026: string | null;
};
