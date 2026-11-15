"""Casos de uso de sistema: saúde do serviço e transparência do método (harmonização, modelo, IPP e fontes)."""
from ..domain.ipp_params import CUT_QUANTILES, FLOOR, WEIGHTS
from ..domain.recommendations import RULES
from ..domain.units import UNIT
from ..infra.firms import Firms
from ..infra.model_store import ModelStore
from ..infra.release import Release

SOURCES = [   # (id, uso, acesso em)
    ('NASA FIRMS · MODIS Aqua, VIIRS S-NPP, NOAA-20', 'série histórica 2003–2025; mês corrente (NRT)', '2026-11-14'),
    ('NOAA CPC · ONI', 'feature climática do modelo', '2026-11-15'),
    ('IBGE · malhas 2024 e população estimada 2024', 'estados, municípios e exposição populacional no Brasil', '2026-11-15'),
    ('FUNAI · terras indígenas (via TerraBrasilis/INPE)', 'exposição E_ti e nome da TI', '2026-11-15'),
    ('Natural Earth 1:50m', 'países e densidade populacional fora do Brasil', '2026-11-14'),
    ('NASA GIBS', 'fundo do mapa', '2026-11-14'),
]


class SystemService:
    def __init__(self, release: Release, firms: Firms, store: ModelStore | None = None):
        self.release, self.firms, self.store = release, firms, store

    def health(self) -> dict:
        return {'status': 'ok', 'release': self.release.version,
                'years': [self.release.years[0], self.release.years[-1]], 'realtime': bool(self.firms.key)}

    def method(self) -> dict:
        m = self.release.manifest
        mm = self.release.model_metrics
        return {'release': self.release.version, 'contract_version': m['contract_version'], 'years': m['years'],
                'rows': m['rows'], 'unit': UNIT, 'metrics': self.release.metrics,
                'quality': {k: v for k, v in m.get('quality', {}).items() if k != 'metrics'},
                'model': {k: v for k, v in mm.items()} or None,
                'ipp': {'weights': WEIGHTS, 'floor': FLOOR, 'cut_quantiles': CUT_QUANTILES,
                        'cuts': self.store.cuts if self.store else {}},
                'rules': {r: {'decisions': d, 'severity': s} for r, (d, s) in RULES.items()},
                'sources': [{'name': n, 'use': u, 'accessed': a} for n, u, a in SOURCES],
                'partial_years': self.release.partial_years,
                'coverage_2026': self.release.partial_years.get('2026', {}).get('coverage') or 'none (FIRMS_MAP_KEY ausente na geração)'}
