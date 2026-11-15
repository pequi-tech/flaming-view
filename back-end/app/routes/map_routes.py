from typing import Annotated

from fastapi import APIRouter, Query

from ..controllers.map_controller import MapController
from ..controllers.input_dto import CellsQueryDTO
from ..controllers.output_dto import CellsResponseDTO, ERROR_RESPONSES


def map_routes(c: MapController) -> APIRouter:
    r = APIRouter(tags=['globo'])

    @r.get('/cells', summary='Atividade de um mês agregada em células (camada do globo)',
           response_model=CellsResponseDTO, responses=ERROR_RESPONSES)
    def cells(query: Annotated[CellsQueryDTO, Query()]):
        return c.cells(query)

    return r
