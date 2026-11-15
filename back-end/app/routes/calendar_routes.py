from typing import Annotated

from fastapi import APIRouter, Query

from ..controllers.calendar_controller import CalendarController
from ..controllers.input_dto import CalendarQueryDTO, SeriesQueryDTO
from ..controllers.output_dto import CalendarResponseDTO, ERROR_RESPONSES, SeriesResponseDTO


def calendar_routes(c: CalendarController) -> APIRouter:
    r = APIRouter(tags=['calendário'])

    @r.get('/calendar', summary='Matriz ano × mês da área, com mediana do mês, razão e nível',
           response_model=CalendarResponseDTO,
           responses={**ERROR_RESPONSES, 200: {'content': {'text/csv': {'schema': {'type': 'string'}}}}})
    def calendar(query: Annotated[CalendarQueryDTO, Query()]):
        return c.calendar(query)

    @r.get('/series', summary='Total anual da área com faixa de incerteza',
           response_model=SeriesResponseDTO, responses=ERROR_RESPONSES)
    def series(query: Annotated[SeriesQueryDTO, Query()]):
        return c.series(query)

    return r
