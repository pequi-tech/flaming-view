from fastapi import APIRouter

from ..controllers.assistant_controller import AssistantController
from ..controllers.assistant_dto import AssistantRequestDTO, ReportRequestDTO
from ..controllers.output_dto import ERROR_RESPONSES

SSE = {200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}}}}


def assistant_routes(c: AssistantController) -> APIRouter:
    r = APIRouter(tags=['assistente'])

    @r.post('/assistant', summary='Pergunta ao assistente ancorado nos dados (SSE)', responses={**ERROR_RESPONSES, **SSE})
    def ask(body: AssistantRequestDTO):
        return c.ask(body)

    @r.post('/assistant/report', summary='Resumo do plano preventivo redigido pelo assistente (SSE)', responses={**ERROR_RESPONSES, **SSE})
    def report(body: ReportRequestDTO):
        return c.report(body)

    return r
