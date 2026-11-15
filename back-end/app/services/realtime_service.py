"""Caso de uso do mês corrente: FIRMS tempo real até hoje, projetado e comparado à climatologia do arquivo."""
import calendar as cal
import datetime as dt

from ..domain.area import BBox
from ..domain.climatology import assess, climatology
from ..domain.projection import project
from ..domain.units import UNIT
from ..infra.firms import Firms
from ..infra.release import Release


def utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


class RealtimeService:
    def __init__(self, release: Release, firms: Firms, today=utc_today):
        self.release, self.firms, self.today = release, firms, today

    def current(self, bbox: BBox) -> dict:
        today = self.today()
        n_days = cal.monthrange(today.year, today.month)[1]
        value, stale = self.firms.cell_days(bbox, today.replace(day=1), today)
        # ponytail: NOAA-21 tratado como S-NPP (fator NOAA-20/S-NPP = 1,01 no pipeline). Calibrar com VIIRS_NOAA21_SP quando precisar.
        val, _, _, _ = self.release.monthly(bbox)
        clim = climatology(val, self.release.baseline_years)[today.month]
        projected = project(value, today.day, n_days)
        return {'area': str(bbox), 'unit': UNIT, 'year': today.year, 'month': today.month, 'day': today.day,
                'days_in_month': n_days, 'value_to_date': value, 'projected': round(projected, 2),
                **assess(projected, clim), 'source': 'nrt', 'satellite': Firms.SOURCE, 'stale': stale}
