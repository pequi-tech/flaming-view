import { useEffect, useState } from "react";
import { ApiError, fireApi } from "./client";
import type { CalendarResponseDTO, CellsResponseDTO, CurrentResponseDTO, HealthResponseDTO, MethodResponseDTO, SeriesResponseDTO } from "./dto";
import type { BBox } from "../geo";
import type { CellsQueryDTO } from "./dto";

export type BackendStatus =
  | { status: "loading" }
  | { status: "online"; health: HealthResponseDTO }
  | { status: "error"; message: string };

export type CountryFireData =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; calendar: CalendarResponseDTO; series: SeriesResponseDTO; current?: CurrentResponseDTO; currentError?: string };

export type CellDataStatus =
  | { status: "idle" | "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: CellsResponseDTO };

export type MethodStatus =
  | { status: "loading" }
  | { status: "loaded"; data: MethodResponseDTO }
  | { status: "error"; message: string };

function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : "Falha ao consultar o backend.";
}

export function useFireData(bbox: BBox | undefined, cellQuery: Omit<CellsQueryDTO, "bbox">, showCells: boolean) {
  const [backend, setBackend] = useState<BackendStatus>({ status: "loading" });
  const [method, setMethod] = useState<MethodStatus>({ status: "loading" });
  const [country, setCountry] = useState<CountryFireData>({ status: "idle" });
  const [cells, setCells] = useState<CellDataStatus>({ status: "idle" });

  useEffect(() => {
    const abort = new AbortController();
    fireApi.health(abort.signal)
      .then((health) => setBackend({ status: "online", health }))
      .catch((error: unknown) => { if (!abort.signal.aborted) setBackend({ status: "error", message: messageOf(error) }); });
    fireApi.method(abort.signal)
      .then((data) => setMethod({ status: "loaded", data }))
      .catch((error: unknown) => { if (!abort.signal.aborted) setMethod({ status: "error", message: messageOf(error) }); });
    return () => abort.abort();
  }, []);

  const online = backend.status === "online";
  const realtime = backend.status === "online" && backend.health.realtime;
  const firstYear = backend.status === "online" ? backend.health.years[0] : undefined;
  const lastYear = backend.status === "online" ? backend.health.years.at(-1) : undefined;

  useEffect(() => {
    if (!bbox) { setCountry({ status: "idle" }); return; }
    if (!online) {
      setCountry(backend.status === "error" ? { status: "error", message: backend.message } : { status: "loading" });
      return;
    }
    const abort = new AbortController();
    setCountry({ status: "loading" });
    const currentRequest = realtime ? fireApi.current({ bbox }, abort.signal) : Promise.resolve(undefined);
    void Promise.allSettled([
      fireApi.calendar({ bbox, from_year: firstYear, to_year: lastYear }, abort.signal),
      fireApi.series({ bbox, from_year: firstYear, to_year: lastYear }, abort.signal),
      currentRequest,
    ]).then(([calendarResult, seriesResult, currentResult]) => {
      if (abort.signal.aborted) return;
      if (calendarResult.status === "rejected") {
        setCountry({ status: "error", message: messageOf(calendarResult.reason) });
        return;
      }
      if (seriesResult.status === "rejected") {
        setCountry({ status: "error", message: messageOf(seriesResult.reason) });
        return;
      }
      setCountry({
        status: "loaded", calendar: calendarResult.value, series: seriesResult.value,
        current: currentResult.status === "fulfilled" ? currentResult.value : undefined,
        currentError: currentResult.status === "rejected" ? messageOf(currentResult.reason) : undefined,
      });
    });
    return () => abort.abort();
  }, [bbox, online, realtime, backend.status, backend.status === "error" ? backend.message : "", firstYear, lastYear]);

  useEffect(() => {
    if (!bbox || !showCells) { setCells({ status: "idle" }); return; }
    if (!online) {
      setCells(backend.status === "error" ? { status: "error", message: backend.message } : { status: "loading" });
      return;
    }
    const abort = new AbortController();
    setCells({ status: "loading" });
    fireApi.cells({ ...cellQuery, bbox }, abort.signal)
      .then((data) => { if (!abort.signal.aborted) setCells({ status: "loaded", data }); })
      .catch((error: unknown) => { if (!abort.signal.aborted) setCells({ status: "error", message: messageOf(error) }); });
    return () => abort.abort();
  }, [bbox, online, backend.status, backend.status === "error" ? backend.message : "", cellQuery.year, cellQuery.month, cellQuery.res, showCells]);

  return { backend, country, cells, method };
}
