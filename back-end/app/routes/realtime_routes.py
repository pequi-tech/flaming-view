from typing import Annotated

from fastapi import APIRouter, Query

from ..controllers.realtime_controller import RealtimeController
from ..controllers.input_dto import CurrentQueryDTO
from ..controllers.output_dto import CurrentResponseDTO, ERROR_RESPONSES


def realtime_routes(c: RealtimeController) -> APIRouter:
    r = APIRouter(tags=['tempo real'])

    @r.get('/current', summary='Mês corrente em tempo real (FIRMS NRT), projetado e comparado à mediana',
           response_model=CurrentResponseDTO, responses=ERROR_RESPONSES)
    def current(query: Annotated[CurrentQueryDTO, Query()]):
        return c.current(query)

    return r
