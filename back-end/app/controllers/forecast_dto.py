"""DTOs da previsão, território, áreas e assistente (contrato 1.1)."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..domain.area import BBox
from .input_dto import InputDTO
from .output_dto import OutputDTO

Level = Literal['baixo', 'normal', 'alto', 'critico']
IppLevel = Literal['baixo', 'medio', 'alto', 'critico']


class AreaRefQueryDTO(InputDTO):
    area_id: str | None = Field(default=None, description='BRA, BR52 (estado), BR5218805 (município) ou ADM0_A3 de país')
    bbox: str | None = Field(default=None, description='oeste,sul,leste,norte; usado se area_id faltar')

    @field_validator('bbox')
    @classmethod
    def check_bbox(cls, v):
        if v is not None:
            BBox.parse(v)
        return v

    @model_validator(mode='after')
    def one_of(self):
        if not self.area_id and not self.bbox:
            raise ValueError('informe area_id ou bbox')
        return self

    @property
    def area(self) -> BBox | None:
        return BBox.parse(self.bbox) if self.bbox else None


class ForecastQueryDTO(AreaRefQueryDTO):
    horizon: int | None = Field(default=None, ge=1, le=3)


class PrioritiesQueryDTO(AreaRefQueryDTO):
    horizon: int = Field(default=1, ge=1, le=3)
    limit: int = Field(default=20, ge=1, le=6000, description='Goiás tem 246 municípios; um município, ~300 células')
    sort: Literal['action', 'fire', 'ipp'] = Field(default='action', description='action = ação mais grave (R8 > R7 > R1 > R2–R4 > R5/R6), desempate por fogo previsto')


class AreasQueryDTO(InputDTO):
    q: str = Field(..., min_length=1, max_length=80)
    limit: int = Field(default=8, ge=1, le=30)


class AreaDTO(OutputDTO):
    id: str
    name: str
    level: str


class HorizonDTO(OutputDTO):
    horizon: int
    forecast_month: str | None
    classes: dict[Level, int]
    cells: int
    predicted: float
    lo: float
    hi: float
    median: float
    p75: float
    p90: float
    ratio: float | None
    level: Level
    last_year: float | None
    metrics: dict[str, Any]


class ForecastResponseDTO(OutputDTO):
    area: AreaDTO
    unit: str
    release: str
    model_version: str | None
    issue_month: str | None
    recent_data: bool
    horizons: list[HorizonDTO]
    lineage: list[AreaDTO] = []


class AreasResponseDTO(OutputDTO):
    query: str
    areas: list[dict[str, Any]]


