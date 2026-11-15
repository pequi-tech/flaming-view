"""HTTP -> saúde e método."""
from ..services.system_service import SystemService
from .output_dto import HealthResponseDTO, MethodResponseDTO
from .responses import json_ok


class SystemController:
    def __init__(self, service: SystemService):
        self.service = service

    def health(self):
        return HealthResponseDTO.model_validate(self.service.health())  # sem cache: monitoramento precisa do estado atual

    def method(self):
        return json_ok(MethodResponseDTO.model_validate(self.service.method()))
