"""Área consultada: caixa W,S,E,N com suporte ao antimeridiano."""
from dataclasses import dataclass

from .errors import InvalidArea

CELL = 0.05                       # grade da release (contract.json)


@dataclass(frozen=True)
class BBox:
    """Caixa W,S,E,N em graus. W > E = cruza o antimeridiano (ex.: Rússia, Fiji)."""
    w: float
    s: float
    e: float
    n: float

    @classmethod
    def parse(cls, text: str) -> 'BBox':
        try:
            w, s, e, n = (float(x) for x in text.split(','))
        except ValueError:
            raise InvalidArea('bbox deve ser "oeste,sul,leste,norte" em graus')
        if not (-180 <= w <= 180 and -180 <= e <= 180):
            raise InvalidArea('longitude fora de [-180, 180]')
        if not (-90 <= s < n <= 90):
            raise InvalidArea('latitude fora de [-90, 90] ou sul >= norte')
        if w == e:
            raise InvalidArea('oeste == leste')
        return cls(w, s, e, n)

    @property
    def crosses_antimeridian(self) -> bool:
        return self.w > self.e

    def lon_ranges(self) -> list[tuple[float, float]]:
        return [(self.w, 180), (-180, self.e)] if self.crosses_antimeridian else [(self.w, self.e)]

    def lat_open_interval(self) -> tuple[float, float]:
        """Cantos SW de célula que intersectam a caixa: s - 0,05 < lat < n (o mesmo vale para cada faixa de lon)."""
        return self.s - CELL, self.n

    def __str__(self):
        return f'{self.w:g},{self.s:g},{self.e:g},{self.n:g}'
