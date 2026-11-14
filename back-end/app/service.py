"""Casos de uso: combinam domínio e infraestrutura. Sem HTTP aqui."""
import calendar as cal
import datetime as dt

from . import domain
from .domain import BBox
from .infra import Firms, Release

UNIT = 'células-dia equivalentes VIIRS S-NPP'


class YearsOutOfRange(ValueError):
    pass


class FireService:
    def __init__(self, release: Release, firms: Firms, today=lambda: dt.datetime.now(dt.timezone.utc).date()):
        self.release, self.firms, self.today = release, firms, today

    def _years(self, from_year, to_year):
        ys = self.release.years
        a, b = from_year or ys[0], to_year or ys[-1]
        if not (ys[0] <= a <= b <= ys[-1]):
            raise YearsOutOfRange(f'anos devem estar em [{ys[0]}, {ys[-1]}] com início <= fim')
        return range(a, b + 1)

    def calendar(self, bbox: BBox, from_year=None, to_year=None):
        years = self._years(from_year, to_year)
        val, lo, hi, src = self.release.monthly(bbox)
        return {'area': str(bbox), 'unit': UNIT, 'release': self.release.version,
                'baseline_years': [self.release.years[0], self.release.years[-1]],
                'months': domain.calendar(val, lo, hi, src, years, self.release.years)}

    def series(self, bbox: BBox, from_year=None, to_year=None):
        years = self._years(from_year, to_year)
        val, lo, hi, src = self.release.monthly(bbox)
        tot = lambda d, y: round(sum(v for (yy, _), v in d.items() if yy == y), 2)
        return {'area': str(bbox), 'unit': UNIT, 'release': self.release.version,
                'years': [{'year': y, 'value': tot(val, y), 'lo': tot(lo, y), 'hi': tot(hi, y), 'source': src.get(y)} for y in years]}

    def cells(self, year, month, res, bbox: BBox | None):
        self._years(year, year)
        rows = self.release.cells(year, month, res, bbox)
        return {'year': year, 'month': month, 'res': res, 'unit': UNIT, 'release': self.release.version,
                'cells': [{'lat': round(a, 4), 'lon': round(b, 4), 'value': round(v, 2)} for a, b, v in rows]}

    def current(self, bbox: BBox):
        """Mês corrente: FIRMS tempo real até hoje, projetado para o mês inteiro e comparado à climatologia do arquivo."""
        today = self.today()
        first = today.replace(day=1)
        n_days = cal.monthrange(today.year, today.month)[1]
        value, stale = self.firms.cell_days(bbox, first, today)
        # ponytail: NOAA-21 tratado como S-NPP (fator NOAA-20/S-NPP = 1,01 no pipeline). Calibrar N21 quando houver 1 ano de arquivo.
        val, _, _, _ = self.release.monthly(bbox)
        clim = domain.climatology(val, self.release.years)[today.month]
        projected = domain.project(value, today.day, n_days)
        return {'area': str(bbox), 'unit': UNIT, 'year': today.year, 'month': today.month, 'day': today.day,
                'days_in_month': n_days, 'value_to_date': value, 'projected': round(projected, 2),
                **domain.assess(projected, clim), 'source': 'nrt', 'satellite': Firms.SOURCE, 'stale': stale}

    def method(self):
        m = self.release.manifest
        return {'release': self.release.version, 'contract_version': m['contract_version'], 'years': m['years'],
                'rows': m['rows'], 'unit': UNIT, 'metrics': self.release.metrics,
                'quality': {k: v for k, v in m.get('quality', {}).items() if k != 'metrics'}}
