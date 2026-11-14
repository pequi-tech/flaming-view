"""Raiz de composição: monta infra -> services -> controllers -> routes. Rodar: uvicorn app.main:create_app --factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .config import Settings
from .controllers.calendar_controller import CalendarController
from .controllers.errors import register_error_handlers
from .controllers.map_controller import MapController
from .controllers.realtime_controller import RealtimeController
from .controllers.system_controller import SystemController
from .infra.cache import Cache
from .infra.firms import Firms, http_get
from .infra.release import Release
from .routes.calendar_routes import calendar_routes
from .routes.map_routes import map_routes
from .routes.realtime_routes import realtime_routes
from .routes.system_routes import system_routes
from .services.calendar_service import CalendarService
from .services.map_service import MapService
from .services.realtime_service import RealtimeService, utc_today
from .services.system_service import SystemService


def create_app(release_dir=None, cache_path=None, map_key=None, fetch=None, today=None, cache_ttl=None) -> FastAPI:
    """Argumentos sobrescrevem o ambiente (usado nos testes para injetar release, FIRMS falso e data)."""
    cfg = Settings()
    release = Release(release_dir or cfg.release_dir, verify_sha=cfg.verify_sha == '1')
    firms = Firms(map_key if map_key is not None else cfg.map_key, Cache(cache_path or cfg.cache_path),
                  fetch or http_get, cfg.realtime_ttl if cache_ttl is None else cache_ttl)

    app = FastAPI(title='Flaming View API', version=release.version,
                  description='Calendário do Fogo: atividade de fogo harmonizada MODIS×VIIRS, 2003→hoje, mundo inteiro.')
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins.split(','), allow_methods=['GET'])
    register_error_handlers(app)

    app.include_router(system_routes(SystemController(SystemService(release, firms))))
    app.include_router(calendar_routes(CalendarController(CalendarService(release))))
    app.include_router(map_routes(MapController(MapService(release))))
    app.include_router(realtime_routes(RealtimeController(RealtimeService(release, firms, today or utc_today))))
    return app
