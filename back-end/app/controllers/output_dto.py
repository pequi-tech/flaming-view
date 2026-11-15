"""Pydantic DTOs for successful and failed HTTP responses."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OutputDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ValidationIssueDTO(OutputDTO):
    field: str
    message: str


class ApiErrorDTO(OutputDTO):
    code: str
    message: str
    details: list[ValidationIssueDTO] | None = None


class ErrorResponseDTO(OutputDTO):
    error: ApiErrorDTO


class CalendarMonthDTO(OutputDTO):
    year: int
    month: int = Field(ge=1, le=12)
    value: float
    lo: float
    hi: float
    median: float
    p75: float
    p90: float
    ratio: float | None
    level: Literal['baixo', 'normal', 'alto', 'critico']
    source: str | None
    estimated: bool


class CalendarResponseDTO(OutputDTO):
    area: str
    unit: str
    release: str
    baseline_years: list[int]
    months: list[CalendarMonthDTO]


class YearTotalDTO(OutputDTO):
    year: int
    value: float
    lo: float
    hi: float
    source: str | None


class SeriesResponseDTO(OutputDTO):
    area: str
    unit: str
    release: str
    years: list[YearTotalDTO]


class CellDTO(OutputDTO):
    id: str | None = None
    lat: float
    lon: float
    value: float
    level: str | None = None


class CellsResponseDTO(OutputDTO):
    year: int | None = None
    month: int | None = None
    res: float | None = None
    layer: str = 'history'
    horizon: int | None = None
    shape: str = 'square'
    h3_res: int | None = None
    cuts: dict[str, float] | None = None
    unit: str
    release: str
    cells: list[CellDTO]


class CurrentResponseDTO(OutputDTO):
    area: str
    unit: str
    year: int
    month: int
    day: int
    days_in_month: int
    value_to_date: float
    projected: float
    median: float
    p75: float
    p90: float
    ratio: float | None
    level: Literal['baixo', 'normal', 'alto', 'critico']
    source: Literal['nrt']
    satellite: str
    stale: bool


class HealthResponseDTO(OutputDTO):
    status: Literal['ok']
    release: str
    years: list[int]
    realtime: bool


class MethodResponseDTO(OutputDTO):
    release: str
    contract_version: str
    years: list[int]
    rows: int
    unit: str
    metrics: dict[str, Any]
    quality: dict[str, Any]
    model: dict[str, Any] | None = None
    ipp: dict[str, Any] | None = None
    rules: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = []
    partial_years: dict[str, Any] = {}
    coverage_2026: str | None = None


ERROR_RESPONSES = {
    404: {'model': ErrorResponseDTO, 'description': 'Rota não encontrada'},
    422: {'model': ErrorResponseDTO, 'description': 'Entrada inválida'},
    500: {'model': ErrorResponseDTO, 'description': 'Erro interno'},
    503: {'model': ErrorResponseDTO, 'description': 'Dependência indisponível'},
}
