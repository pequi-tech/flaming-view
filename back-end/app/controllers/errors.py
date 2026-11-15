"""Intercepta erros de rota e negócio e serializa um único DTO de erro."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..domain.errors import AssistantUnavailable, InvalidArea, ModelUnavailable, NotFound, RealtimeUnavailable, YearsOutOfRange
from .output_dto import ApiErrorDTO, ErrorResponseDTO, ValidationIssueDTO

logger = logging.getLogger(__name__)


def _error(status: int, code: str, message: str, *, details=None, headers=None) -> JSONResponse:
    body = ErrorResponseDTO(error=ApiErrorDTO(code=code, message=message, details=details))
    return JSONResponse(body.model_dump(mode='json', exclude_none=True), status_code=status, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, e: RequestValidationError):
        details = [ValidationIssueDTO(
            field='.'.join(str(part) for part in issue['loc']), message=issue['msg'])
            for issue in e.errors()]
        return _error(422, 'invalid_request', 'A solicitação contém campos inválidos.', details=details)

    @app.exception_handler(InvalidArea)
    async def invalid_area(_: Request, e: InvalidArea):
        return _error(422, 'invalid_area', str(e))

    @app.exception_handler(YearsOutOfRange)
    async def years_out_of_range(_: Request, e: YearsOutOfRange):
        return _error(422, 'years_out_of_range', str(e))

    @app.exception_handler(RealtimeUnavailable)
    async def realtime_down(_: Request, __: RealtimeUnavailable):
        return _error(503, 'realtime_unavailable', 'Tempo real indisponível no momento.')

    @app.exception_handler(NotFound)
    async def not_found(_: Request, e: NotFound):
        return _error(404, 'not_found', str(e))

    @app.exception_handler(ModelUnavailable)
    async def model_down(_: Request, __: ModelUnavailable):
        return _error(503, 'model_unavailable', 'Esta release não tem previsão publicada.')

    @app.exception_handler(AssistantUnavailable)
    async def assistant_down(_: Request, __: AssistantUnavailable):
        return _error(503, 'assistant_unavailable', 'Assistente indisponível: sem chave da API no servidor.')

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, e: StarletteHTTPException):
        code = 'not_found' if e.status_code == 404 else 'http_error'
        message = e.detail if isinstance(e.detail, str) else 'A solicitação não pôde ser processada.'
        return _error(e.status_code, code, message, headers=e.headers)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        logger.exception('Erro não tratado na API', exc_info=e)
        return _error(500, 'internal_error', 'Erro interno do serviço.')
