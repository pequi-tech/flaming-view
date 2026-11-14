"""Caso de uso do globo: atividade de um mês agregada em células."""
from ..domain.area import BBox
from ..domain.units import UNIT
from ..domain.years import year_range
from ..infra.release import Release


class MapService:
    def __init__(self, release: Release):
        self.release = release

    def cells(self, year: int, month: int, res: float, bbox: BBox | None) -> dict:
        year_range(self.release.years, year, year)
        rows = self.release.cells(year, month, res, bbox)
        return {'year': year, 'month': month, 'res': res, 'unit': UNIT, 'release': self.release.version,
                'cells': [{'lat': round(a, 4), 'lon': round(b, 4), 'value': round(v, 2)} for a, b, v in rows]}
