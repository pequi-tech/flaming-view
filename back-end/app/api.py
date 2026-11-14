"""HTTP: rotas, validação de entrada, cache HTTP e CSV. A lógica está em service/domain."""
import csv, io, os
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response

from .domain import BBox, InvalidArea
from .infra import Cache, Firms, FirmsUnavailable, Release, http_get
from .service import FireService, YearsOutOfRange

ARCHIVE_CACHE = 'public, max-age=86400'      # release é imutável; muda de versão, muda a resposta
LIVE_CACHE = 'public, max-age=300'
RESOLUTIONS = (0.25, 0.5, 1.0, 2.0)
CSV_COLS = ['year', 'month', 'value', 'lo', 'hi', 'median', 'p75', 'p90', 'ratio', 'level', 'source', 'estimated']


def create_app(release_dir=None, cache_path=None, map_key=None, fetch=None, today=None, cache_ttl=3600):
    env = os.environ.get
    release = Release(release_dir or env('FV_RELEASE', '../serving/release'), verify_sha=env('FV_VERIFY_SHA') == '1')
    cache = Cache(cache_path or env('FV_CACHE', 'cache.db'))
    firms = Firms(map_key if map_key is not None else env('FIRMS_MAP_KEY'), cache, fetch or http_get, cache_ttl)
    svc = FireService(release, firms, **({'today': today} if today else {}))

    app = FastAPI(title='Flaming View API', version=release.version,
                  description='Calendário do Fogo: atividade de fogo harmonizada MODIS×VIIRS, 2003→hoje, mundo inteiro.')
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CORSMiddleware, allow_origins=env('FV_CORS', '*').split(','), allow_methods=['GET'])

    @app.exception_handler(InvalidArea)
    @app.exception_handler(YearsOutOfRange)
    def bad_input(_: Request, e: Exception):
        return JSONResponse({'detail': str(e)}, status_code=422)

    @app.exception_handler(FirmsUnavailable)
    def firms_down(_: Request, e: Exception):
        return JSONResponse({'detail': f'tempo real indisponível: {e}'}, status_code=503)

    def ok(body, cache_control=ARCHIVE_CACHE):
        return JSONResponse(body, headers={'Cache-Control': cache_control})

    BBOX = Query(..., description='oeste,sul,leste,norte em graus; oeste > leste cruza o antimeridiano', examples=['-58,-22,-54,-16'])

    @app.get('/health')
    def health():
        return {'status': 'ok', 'release': release.version, 'years': [release.years[0], release.years[-1]],
                'realtime': bool(firms.key)}

    @app.get('/calendar', summary='Matriz ano × mês da área, com mediana do mês, razão e nível')
    def calendar(bbox: str = BBOX, from_year: int | None = None, to_year: int | None = None,
                 format: Literal['json', 'csv'] = 'json'):
        body = svc.calendar(BBox.parse(bbox), from_year, to_year)
        if format == 'json':
            return ok(body)
        buf = io.StringIO()
        w = csv.DictWriter(buf, CSV_COLS, extrasaction='ignore')
        w.writeheader()
        w.writerows(body['months'])
        return Response(buf.getvalue(), media_type='text/csv', headers={
            'Cache-Control': ARCHIVE_CACHE, 'Content-Disposition': f'attachment; filename="calendario_{bbox}.csv"'})

    @app.get('/series', summary='Total anual da área com faixa de incerteza')
    def series(bbox: str = BBOX, from_year: int | None = None, to_year: int | None = None):
        return ok(svc.series(BBox.parse(bbox), from_year, to_year))

    @app.get('/cells', summary='Atividade de um mês agregada em células (camada do globo)')
    def cells(year: int, month: int = Query(..., ge=1, le=12), res: float = 1.0, bbox: str | None = None):
        if res not in RESOLUTIONS:
            raise HTTPException(422, f'res deve ser um de {RESOLUTIONS}')
        return ok(svc.cells(year, month, res, BBox.parse(bbox) if bbox else None))

    @app.get('/current', summary='Mês corrente em tempo real (FIRMS NRT), projetado e comparado à mediana')
    def current(bbox: str = BBOX):
        return ok(svc.current(BBox.parse(bbox)), LIVE_CACHE)

    @app.get('/method', summary='Validação da harmonização e qualidade da release')
    def method():
        return ok(svc.method())

    return app

