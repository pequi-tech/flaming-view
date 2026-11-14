"""Formatos de resposta HTTP e política de cache do navegador/CDN."""
import csv, io

from fastapi.responses import JSONResponse, Response

ARCHIVE_CACHE = 'public, max-age=86400'      # release é imutável; muda de versão, muda a resposta
LIVE_CACHE = 'public, max-age=300'


def json_ok(body: dict, cache_control: str = ARCHIVE_CACHE) -> JSONResponse:
    return JSONResponse(body, headers={'Cache-Control': cache_control})


def csv_download(rows: list[dict], columns: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.DictWriter(buf, columns, extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return Response(buf.getvalue(), media_type='text/csv', headers={
        'Cache-Control': ARCHIVE_CACHE, 'Content-Disposition': f'attachment; filename="{filename}"'})
