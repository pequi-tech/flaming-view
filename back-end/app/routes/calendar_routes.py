from typing import Literal

from fastapi import APIRouter

from ..controllers.calendar_controller import CalendarController
from .params import BBOX


def calendar_routes(c: CalendarController) -> APIRouter:
    r = APIRouter(tags=['calendário'])

    @r.get('/calendar', summary='Matriz ano × mês da área, com mediana do mês, razão e nível')
    def calendar(bbox: str = BBOX, from_year: int | None = None, to_year: int | None = None,
                 format: Literal['json', 'csv'] = 'json'):
        return c.calendar(bbox, from_year, to_year, format)

    @r.get('/series', summary='Total anual da área com faixa de incerteza')
    def series(bbox: str = BBOX, from_year: int | None = None, to_year: int | None = None):
        return c.series(bbox, from_year, to_year)

    return r
