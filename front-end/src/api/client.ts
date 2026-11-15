import type {
  CalendarQueryDTO, CalendarResponseDTO, CellsQueryDTO, CellsResponseDTO,
  CurrentQueryDTO, CurrentResponseDTO, ErrorResponseDTO, HealthResponseDTO,
  MethodResponseDTO, SeriesQueryDTO, SeriesResponseDTO,
} from "./dto";
import type { BBox } from "../geo";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly details?: ErrorResponseDTO["error"]["details"]) {
    super(message);
    this.name = "ApiError";
  }
}

function longitudeForApi(value: number): number {
  const wrapped = ((value + 180) % 360 + 360) % 360 - 180;
  return wrapped === -180 && value > 0 ? 180 : wrapped;
}

export function bboxParam([west, south, east, north]: BBox): string {
  return [longitudeForApi(west), south, longitudeForApi(east), north]
    .map((value) => Number(value.toFixed(6)))
    .join(",");
}

function queryUrl(path: string, values: Record<string, string | number | undefined>) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) url.searchParams.set(key, String(value));
  }
  return url;
}

async function get<T>(path: string, values: Record<string, string | number | undefined> = {}, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(queryUrl(path, values), { headers: { Accept: "application/json" }, cache: "no-cache", signal });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, "backend_unavailable", "Não foi possível conectar ao backend.");
  }

  const body: unknown = await response.json().catch(() => undefined);
  if (!response.ok) {
    const error = body && typeof body === "object" && "error" in body
      ? (body as ErrorResponseDTO).error
      : { code: "invalid_response", message: "O backend retornou uma resposta inválida." };
    throw new ApiError(response.status, error.code, error.message, error.details);
  }
  if (body === undefined) throw new ApiError(response.status, "invalid_response", "O backend retornou JSON inválido.");
  return body as T;
}

export const fireApi = {
  health: (signal?: AbortSignal) => get<HealthResponseDTO>("/health", {}, signal),
  method: (signal?: AbortSignal) => get<MethodResponseDTO>("/method", {}, signal),
  calendar: (query: CalendarQueryDTO, signal?: AbortSignal) => get<CalendarResponseDTO>("/calendar", {
    bbox: bboxParam(query.bbox), from_year: query.from_year, to_year: query.to_year,
  }, signal),
  series: (query: SeriesQueryDTO, signal?: AbortSignal) => get<SeriesResponseDTO>("/series", {
    bbox: bboxParam(query.bbox), from_year: query.from_year, to_year: query.to_year,
  }, signal),
  cells: (query: CellsQueryDTO, signal?: AbortSignal) => get<CellsResponseDTO>("/cells", {
    year: query.year, month: query.month, res: query.res, bbox: query.bbox ? bboxParam(query.bbox) : undefined,
  }, signal),
  current: (query: CurrentQueryDTO, signal?: AbortSignal) => get<CurrentResponseDTO>("/current", {
    bbox: bboxParam(query.bbox),
  }, signal),
  calendarCsv: async (query: CalendarQueryDTO, signal?: AbortSignal): Promise<Blob> => {
    const response = await fetch(queryUrl("/calendar", {
      bbox: bboxParam(query.bbox), from_year: query.from_year, to_year: query.to_year, format: "csv",
    }), { headers: { Accept: "text/csv" }, signal });
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined);
      const error = body && typeof body === "object" && "error" in body
        ? (body as ErrorResponseDTO).error
        : { code: "export_failed", message: "Não foi possível exportar o calendário." };
      throw new ApiError(response.status, error.code, error.message, error.details);
    }
    return response.blob();
  },
};

// ---- contrato 1.1 ----
import type { AreaHit, CellResponseDTO, ForecastResponseDTO, LayerResponseDTO, MethodV2, PrioritiesResponseDTO } from "./dto";

type AreaQ = { area_id?: string; bbox?: BBox };
const areaParams = (q: AreaQ) => ({ area_id: q.area_id, bbox: q.bbox && !q.area_id ? bboxParam(q.bbox) : undefined });

export const fvApi = {
  method: (signal?: AbortSignal) => get<MethodV2>("/method", {}, signal),
  forecast: (q: AreaQ, signal?: AbortSignal) => get<ForecastResponseDTO>("/forecast", areaParams(q), signal),
  priorities: (q: AreaQ & { horizon: number; limit?: number; sort?: "action" | "fire" | "ipp" }, signal?: AbortSignal) =>
    get<PrioritiesResponseDTO>("/priorities", { ...areaParams(q), horizon: q.horizon, limit: q.limit ?? 20, sort: q.sort }, signal),
  cell: (id: number | string, signal?: AbortSignal) => get<CellResponseDTO>(`/cell/${id}`, {}, signal),
  areas: (q: string, signal?: AbortSignal) => get<{ query: string; areas: AreaHit[] }>("/areas", { q, limit: 8 }, signal),
  geometry: (id: string, signal?: AbortSignal) => get<any>(`/areas/${encodeURIComponent(id)}/geometry`, {}, signal),
  layer: (q: AreaQ & { layer: "history" | "forecast" | "ipp"; horizon: number; h3_res?: number; year?: number; month?: number }, signal?: AbortSignal) =>
    get<LayerResponseDTO>("/cells", { ...areaParams(q), layer: q.layer, horizon: q.horizon, shape: q.h3_res ? "h3" : "square",
      h3_res: q.h3_res, year: q.year, month: q.month }, signal),
};

/** POST com resposta SSE (`data: {"text"}` … `data: [DONE]`). Chama onText a cada pedaço. 503 vira ApiError. */
export async function streamPost(path: string, body: unknown, onText: (t: string) => void, signal?: AbortSignal) {
  const r = await fetch(`${API_BASE}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal })
    .catch(() => { throw new ApiError(0, "backend_unavailable", "Não foi possível conectar ao backend."); });
  if (!r.ok || !r.body) {
    const e = await r.json().catch(() => undefined) as ErrorResponseDTO | undefined;
    throw new ApiError(r.status, e?.error.code ?? "http_error", e?.error.code === "assistant_unavailable" ? "no_key" : e?.error.message ?? "Falha no assistente.");
  }
  const reader = r.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buf += value;
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const line = buf.slice(0, i).replace(/^data: /, ""); buf = buf.slice(i + 2);
      if (line === "[DONE]") return;
      const msg = JSON.parse(line);
      if (msg.error) throw new ApiError(503, msg.error, msg.reason ?? "upstream");
      onText(msg.text);
    }
  }
}
