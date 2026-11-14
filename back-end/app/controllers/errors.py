"""Tradução dos erros de negócio em status HTTP."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..domain.errors import InvalidArea, RealtimeUnavailable, YearsOutOfRange


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidArea)
    @app.exception_handler(YearsOutOfRange)
    def bad_input(_: Request, e: Exception):
        return JSONResponse({'detail': str(e)}, status_code=422)

    @app.exception_handler(RealtimeUnavailable)
    def realtime_down(_: Request, e: Exception):
        return JSONResponse({'detail': f'tempo real indisponível: {e}'}, status_code=503)
