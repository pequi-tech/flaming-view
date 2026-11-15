from fastapi import APIRouter

from ..controllers.system_controller import SystemController
from ..controllers.output_dto import HealthResponseDTO, MethodResponseDTO, ERROR_RESPONSES


def system_routes(c: SystemController) -> APIRouter:
    r = APIRouter(tags=['sistema'])

    @r.get('/health', summary='Estado do serviço e da release',
           response_model=HealthResponseDTO, responses=ERROR_RESPONSES)
    def health():
        return c.health()

    @r.get('/method', summary='Validação da harmonização e qualidade da release',
           response_model=MethodResponseDTO, responses=ERROR_RESPONSES)
    def method():
        return c.method()

    return r
