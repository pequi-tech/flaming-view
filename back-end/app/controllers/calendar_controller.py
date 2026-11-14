"""HTTP -> calendário/série: converte a área e escolhe JSON ou CSV."""
from ..domain.area import BBox
from ..services.calendar_service import CalendarService
from .responses import csv_download, json_ok

CSV_COLUMNS = ['year', 'month', 'value', 'lo', 'hi', 'median', 'p75', 'p90', 'ratio', 'level', 'source', 'estimated']


class CalendarController:
    def __init__(self, service: CalendarService):
        self.service = service

    def calendar(self, bbox: str, from_year: int | None, to_year: int | None, format: str):
        body = self.service.calendar(BBox.parse(bbox), from_year, to_year)
        if format == 'csv':
            return csv_download(body['months'], CSV_COLUMNS, f'calendario_{bbox}.csv')
        return json_ok(body)

    def series(self, bbox: str, from_year: int | None, to_year: int | None):
        return json_ok(self.service.series(BBox.parse(bbox), from_year, to_year))
