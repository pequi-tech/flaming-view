"""HTTP -> mês corrente (cache curto: o dado muda ao longo do dia)."""
from ..domain.area import BBox
from ..services.realtime_service import RealtimeService
from .responses import LIVE_CACHE, json_ok


class RealtimeController:
    def __init__(self, service: RealtimeService):
        self.service = service

    def current(self, bbox: str):
        return json_ok(self.service.current(BBox.parse(bbox)), LIVE_CACHE)
