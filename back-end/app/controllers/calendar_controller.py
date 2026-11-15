"""HTTP -> calendário/série: converte a área e escolhe JSON ou CSV."""
from ..services.calendar_service import CalendarService
from .input_dto import CalendarQueryDTO, SeriesQueryDTO
from .output_dto import CalendarResponseDTO, SeriesResponseDTO
from .responses import csv_download, json_ok

CSV_COLUMNS = ['year', 'month', 'value', 'lo', 'hi', 'median', 'p75', 'p90', 'ratio', 'level', 'source', 'estimated']


class CalendarController:
    def __init__(self, service: CalendarService):
        self.service = service

    def calendar(self, query: CalendarQueryDTO):
        body = CalendarResponseDTO.model_validate(
            self.service.calendar(query.area, query.from_year, query.to_year))
        if query.format == 'csv':
            rows = [month.model_dump(mode='json') for month in body.months]
            return csv_download(rows, CSV_COLUMNS, f'calendario_{query.bbox}.csv')
        return json_ok(body)

    def series(self, query: SeriesQueryDTO):
        body = SeriesResponseDTO.model_validate(
            self.service.series(query.area, query.from_year, query.to_year))
        return json_ok(body)
