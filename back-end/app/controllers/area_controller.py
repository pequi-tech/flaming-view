"""HTTP -> busca de áreas e geometria."""
from fastapi.responses import JSONResponse

from ..services.area_service import AreaService
from .forecast_dto import AreasQueryDTO, AreasResponseDTO
from .responses import ARCHIVE_CACHE, json_ok


class AreaController:
    def __init__(self, areas: AreaService):
        self.areas = areas

    def search(self, q: AreasQueryDTO):
        return json_ok(AreasResponseDTO.model_validate(self.areas.search(q.q, q.limit)))

    def geometry(self, area_id: str):
        return JSONResponse(self.areas.geometry(area_id), headers={'Cache-Control': ARCHIVE_CACHE})
