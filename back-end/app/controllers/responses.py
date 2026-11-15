"""Formatos de resposta HTTP e política de cache do navegador/CDN."""
import csv, io

from pydantic import BaseModel
from fastapi.responses import JSONResponse, Response

ARCHIVE_CACHE = 'public, max-age=60'        # a URL não carrega a versão da release; republicar tem de aparecer logo
LIVE_CACHE = 'public, max-age=300'


def json_ok(body: BaseModel, cache_control: str = ARCHIVE_CACHE) -> JSONResponse:
    """Serializa somente DTOs já validados para manter o contrato de saída explícito."""
    return JSONResponse(body.model_dump(mode='json'), headers={'Cache-Control': cache_control})


def csv_download(rows: list[dict], columns: list[str], filename: str) -> Response:
    buf = io.StringIO()
    w = csv.DictWriter(buf, columns, extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)
    return Response(buf.getvalue(), media_type='text/csv', headers={
        'Cache-Control': ARCHIVE_CACHE, 'Content-Disposition': f'attachment; filename="{filename}"'})
