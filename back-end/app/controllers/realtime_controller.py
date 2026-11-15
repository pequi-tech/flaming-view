"""HTTP -> mês corrente (cache curto: o dado muda ao longo do dia)."""
from ..services.realtime_service import RealtimeService
from .input_dto import CurrentQueryDTO
from .output_dto import CurrentResponseDTO
from .responses import LIVE_CACHE, json_ok


class RealtimeController:
    def __init__(self, service: RealtimeService):
        self.service = service

    def current(self, query: CurrentQueryDTO):
        body = CurrentResponseDTO.model_validate(self.service.current(query.area))
        return json_ok(body, LIVE_CACHE)
