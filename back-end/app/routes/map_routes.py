from fastapi import APIRouter, Query

from ..controllers.map_controller import MapController


def map_routes(c: MapController) -> APIRouter:
    r = APIRouter(tags=['globo'])

    @r.get('/cells', summary='Atividade de um mês agregada em células (camada do globo)')
    def cells(year: int, month: int = Query(..., ge=1, le=12), res: float = 1.0, bbox: str | None = None):
        return c.cells(year, month, res, bbox)

    return r
