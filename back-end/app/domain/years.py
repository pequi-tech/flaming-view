"""Período consultado dentro do arquivo publicado."""
from .errors import YearsOutOfRange


def year_range(available: list[int], from_year: int | None = None, to_year: int | None = None) -> range:
    a, b = from_year or available[0], to_year or available[-1]
    if not (available[0] <= a <= b <= available[-1]):
        raise YearsOutOfRange(f'anos devem estar em [{available[0]}, {available[-1]}] com início <= fim')
    return range(a, b + 1)
