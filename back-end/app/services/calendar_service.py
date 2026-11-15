"""Casos de uso do calendário: matriz ano × mês e série anual de uma área."""
from ..domain.area import BBox
from ..domain.calendar import calendar, yearly_totals
from ..domain.units import UNIT
from ..domain.years import year_range
from ..infra.release import Release


class CalendarService:
    def __init__(self, release: Release):
        self.release = release

    def calendar(self, bbox: BBox, from_year=None, to_year=None) -> dict:
        years = year_range(self.release.years, from_year, to_year)
        val, lo, hi, src = self.release.monthly(bbox)
        return {'area': str(bbox), 'unit': UNIT, 'release': self.release.version,
                'baseline_years': [self.release.baseline_years[0], self.release.baseline_years[-1]],
                'months': calendar(val, lo, hi, src, years, self.release.baseline_years)}

    def series(self, bbox: BBox, from_year=None, to_year=None) -> dict:
        years = year_range(self.release.years, from_year, to_year)
        val, lo, hi, src = self.release.monthly(bbox)
        return {'area': str(bbox), 'unit': UNIT, 'release': self.release.version,
                'years': yearly_totals(val, lo, hi, src, years)}
