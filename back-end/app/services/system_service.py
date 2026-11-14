"""Casos de uso de sistema: saúde do serviço e transparência do método."""
from ..domain.units import UNIT
from ..infra.firms import Firms
from ..infra.release import Release


class SystemService:
    def __init__(self, release: Release, firms: Firms):
        self.release, self.firms = release, firms

    def health(self) -> dict:
        return {'status': 'ok', 'release': self.release.version,
                'years': [self.release.years[0], self.release.years[-1]], 'realtime': bool(self.firms.key)}

    def method(self) -> dict:
        m = self.release.manifest
        return {'release': self.release.version, 'contract_version': m['contract_version'], 'years': m['years'],
                'rows': m['rows'], 'unit': UNIT, 'metrics': self.release.metrics,
                'quality': {k: v for k, v in m.get('quality', {}).items() if k != 'metrics'}}
