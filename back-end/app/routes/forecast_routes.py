from typing import Annotated

from fastapi import APIRouter, Path, Query

from ..controllers.forecast_controller import ForecastController
from ..controllers.forecast_dto import ForecastQueryDTO, ForecastResponseDTO, PrioritiesQueryDTO
from ..controllers.output_dto import ERROR_RESPONSES
from ..controllers.territory_dto import CellResponseDTO, PrioritiesResponseDTO


def forecast_routes(c: ForecastController) -> APIRouter:
    r = APIRouter(tags=['previsão'])

    @r.get('/forecast', summary='Classe prevista M+1..M+3 da área, total previsto com faixa, mediana do mês e métricas',
           response_model=ForecastResponseDTO, responses=ERROR_RESPONSES)
    def forecast(query: Annotated[ForecastQueryDTO, Query()]):
        return c.forecast(query)

    @r.get('/priorities', summary='Municípios, células ou hexágonos ordenados pelo IPP, com recomendações',
           response_model=PrioritiesResponseDTO, responses=ERROR_RESPONSES)
    def priorities(query: Annotated[PrioritiesQueryDTO, Query()]):
        return c.priorities(query)

    @r.get('/cell/{cell_id}', summary='Detalhe da célula 0,05°: lugar, previsão, IPP, histórico, fatores e recomendações',
           response_model=CellResponseDTO, responses=ERROR_RESPONSES)
    def cell(cell_id: Annotated[int, Path(ge=0, le=25_919_999)]):
        return c.cell(cell_id)

    return r
