"""HTTP -> camada do globo: valida a resolução pedida."""
from fastapi import HTTPException

from ..domain.area import BBox
from ..services.map_service import MapService
from .responses import json_ok

RESOLUTIONS = (0.25, 0.5, 1.0, 2.0)


class MapController:
    def __init__(self, service: MapService):
        self.service = service

    def cells(self, year: int, month: int, res: float, bbox: str | None):
        if res not in RESOLUTIONS:
            raise HTTPException(422, f'res deve ser um de {RESOLUTIONS}')
        return json_ok(self.service.cells(year, month, res, BBox.parse(bbox) if bbox else None))
