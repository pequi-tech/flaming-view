"""HTTP -> previsão por área, prioridades e detalhe da célula."""
from ..services.area_service import AreaService
from ..services.forecast_service import ForecastService
from ..services.territory_service import TerritoryService
from .forecast_dto import ForecastQueryDTO
from .responses import json_ok
from .forecast_dto import PrioritiesQueryDTO
from .territory_dto import CellResponseDTO, PrioritiesResponseDTO
from .forecast_dto import ForecastResponseDTO


class ForecastController:
    def __init__(self, forecast: ForecastService, territory: TerritoryService, areas: AreaService):
        self.forecast_s, self.territory, self.areas = forecast, territory, areas

    def forecast(self, q: ForecastQueryDTO):
        area = self.areas.resolve(q.area_id, q.area)
        body = self.forecast_s.forecast(area, (q.horizon,) if q.horizon else (1, 2, 3))
        body['lineage'] = self.areas.lineage(area) if q.area_id else []
        return json_ok(ForecastResponseDTO.model_validate(body))

    def priorities(self, q: PrioritiesQueryDTO):
        area = self.areas.resolve(q.area_id, q.area)
        return json_ok(PrioritiesResponseDTO.model_validate(self.territory.priorities(area, q.horizon, q.limit, q.sort)))

    def cell(self, cell_id: int):
        return json_ok(CellResponseDTO.model_validate(self.territory.cell(cell_id)))
