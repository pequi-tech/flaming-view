from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..controllers.area_controller import AreaController
from ..controllers.forecast_dto import AreasQueryDTO, AreasResponseDTO
from ..controllers.output_dto import ERROR_RESPONSES


def area_routes(c: AreaController) -> APIRouter:
    r = APIRouter(tags=['áreas'])

    @r.get('/areas', summary='Busca país, estado ou município por prefixo, sem acento',
           response_model=AreasResponseDTO, responses=ERROR_RESPONSES)
    def search(query: Annotated[AreasQueryDTO, Query()]):
        return c.search(query)

    @r.get('/areas/{area_id}/geometry', summary='GeoJSON simplificado da área', responses=ERROR_RESPONSES)
    def geometry(area_id: Annotated[str, Path(max_length=16)]):
        return c.geometry(area_id)

    return r
