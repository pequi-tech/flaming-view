"""Pydantic DTOs for query parameters accepted by the HTTP routes."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..domain.area import BBox


class InputDTO(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AreaQueryDTO(InputDTO):
    bbox: str = Field(..., description='oeste,sul,leste,norte em graus; oeste > leste cruza o antimeridiano')

    @field_validator('bbox')
    @classmethod
    def validate_bbox(cls, value: str) -> str:
        BBox.parse(value)
        return value

    @property
    def area(self) -> BBox:
        return BBox.parse(self.bbox)


class AreaPeriodQueryDTO(AreaQueryDTO):
    from_year: int | None = Field(default=None, ge=1)
    to_year: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def validate_year_order(self):
        if self.from_year is not None and self.to_year is not None and self.from_year > self.to_year:
            raise ValueError('from_year deve ser menor ou igual a to_year')
        return self


class CalendarQueryDTO(AreaPeriodQueryDTO):
    format: Literal['json', 'csv'] = 'json'


class SeriesQueryDTO(AreaPeriodQueryDTO):
    pass


class CurrentQueryDTO(AreaQueryDTO):
    pass


class CellsQueryDTO(InputDTO):
    year: int | None = Field(default=None, ge=1, description='obrigatório em layer=history')
    month: int | None = Field(default=None, ge=1, le=12)
    res: float = 1.0
    layer: Literal['history', 'forecast', 'ipp'] = 'history'
    horizon: int = Field(default=1, ge=1, le=3)
    shape: Literal['square', 'h3'] = 'square'
    h3_res: int = Field(default=5, ge=4, le=6)
    area_id: str | None = Field(default=None, description='recorta pelas células da área (BRA, BR52, BR5218805)')
    bbox: str | None = Field(default=None, description='oeste,sul,leste,norte; omitido = mundo inteiro')

    @field_validator('res')
    @classmethod
    def validate_resolution(cls, value: float) -> float:
        if value not in (0.25, 0.5, 1.0, 2.0):
            raise ValueError('res deve ser um de 0.25, 0.5, 1 ou 2 graus')
        return value

    @field_validator('bbox')
    @classmethod
    def validate_optional_bbox(cls, value: str | None) -> str | None:
        if value is not None:
            BBox.parse(value)
        return value

    @model_validator(mode='after')
    def history_needs_period(self):
        if self.layer == 'history' and (self.year is None or self.month is None):
            raise ValueError('layer=history exige year e month')
        return self

    @property
    def area(self) -> BBox | None:
        return BBox.parse(self.bbox) if self.bbox is not None else None
