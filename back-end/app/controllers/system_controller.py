"""HTTP -> saúde e método."""
from ..services.system_service import SystemService
from .responses import json_ok


class SystemController:
    def __init__(self, service: SystemService):
        self.service = service

    def health(self):
        return self.service.health()                  # sem cache: monitoramento precisa do estado atual

    def method(self):
        return json_ok(self.service.method())
