"""DTOs do território: prioridades, célula e recomendações."""
from typing import Any, Literal

from pydantic import ConfigDict

from .forecast_dto import AreaDTO, IppLevel, Level
from .output_dto import OutputDTO


class RecommendationDTO(OutputDTO):
    rule_id: str
    decisions: list[str]
    severity: Literal['high', 'medium', 'low']
    key: str


class IppDTO(OutputDTO):
    value: float
    level: IppLevel
    n: float
    v: float
    e: float
    explanation: dict[str, Any]


class PriorityItemDTO(IppDTO):
    id: str
    kind: Literal['municipality', 'cell', 'hexagon']
    name: str | None
    ipp: float
    forecast_level: Level
    predicted: float
    cells: int
    critical_cells: int
    ti_name: str | None
    lat: float
    lon: float
    recommendations: list[RecommendationDTO]


class PrioritiesResponseDTO(OutputDTO):
    area: AreaDTO
    horizon: int
    granularity: str
    sort: str
    total: int
    release: str
    cuts: dict[str, float]
    items: list[PriorityItemDTO]


class CellResponseDTO(OutputDTO):
    model_config = ConfigDict(extra='forbid')
    cell_id: int
    lat: float
    lon: float
    release: str
    model_version: str
    recent_data: bool
    issue_month: str
    place: dict[str, Any]
    exposure: dict[str, Any]
    forecast: list[dict[str, Any]]
    history: list[dict[str, Any]]
    climatology: list[dict[str, Any]]
    drivers: list[dict[str, Any]]
    recommendations: list[RecommendationDTO]


