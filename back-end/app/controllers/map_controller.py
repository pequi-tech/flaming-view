"""HTTP -> camada do mapa: histórico em quadrados (globo) ou previsão/IPP/histórico agregados em hexágonos H3."""
from ..services.area_service import AreaService
from ..services.forecast_service import ForecastService
from ..services.map_service import MapService
from .input_dto import CellsQueryDTO
from .output_dto import CellsResponseDTO
from .responses import json_ok


class MapController:
    def __init__(self, service: MapService, forecast: ForecastService | None = None, areas: AreaService | None = None):
        self.service, self.forecast, self.areas = service, forecast, areas

    def cells(self, query: CellsQueryDTO):
        if query.layer == 'history' and query.shape == 'square':
            body = self.service.cells(query.year, query.month, query.res, query.area)
        else:
            area = self.areas.resolve(query.area_id, query.area) if query.area_id else None
            h3 = query.h3_res if query.shape == 'h3' else None
            body = self.forecast.cells(query.layer, query.horizon, h3, area, query.area, query.year, query.month)
            if query.layer == 'history':
                body.update(year=query.year, month=query.month)
        return json_ok(CellsResponseDTO.model_validate(body))
