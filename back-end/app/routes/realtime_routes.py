from fastapi import APIRouter

from ..controllers.realtime_controller import RealtimeController
from .params import BBOX


def realtime_routes(c: RealtimeController) -> APIRouter:
    r = APIRouter(tags=['tempo real'])

    @r.get('/current', summary='Mês corrente em tempo real (FIRMS NRT), projetado e comparado à mediana')
    def current(bbox: str = BBOX):
        return c.current(bbox)

    return r
