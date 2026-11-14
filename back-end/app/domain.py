"""Domínio: área consultada, climatologia e classificação do mês. Puro, sem IO."""
from dataclasses import dataclass
import numpy as np

CELL = 0.05                       # grade da release (contract.json)
LEVELS = ('baixo', 'normal', 'alto', 'critico')


class InvalidArea(ValueError):
    pass


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


def climatology(values: dict, years) -> dict:
    """Por mês: p25, mediana, p75, p90 sobre os anos de base. Ano sem linha = zero (a release só guarda células com fogo)."""
    out = {}
    for m in range(1, 13):
        v = np.array([values.get((y, m), 0.0) for y in years])
        p25, med, p75, p90 = np.percentile(v, [25, 50, 75, 90]) if len(v) else (0, 0, 0, 0)
        out[m] = {'p25': float(p25), 'median': float(med), 'p75': float(p75), 'p90': float(p90)}
    return out


def assess(value: float, clim: dict) -> dict:
    """Razão sobre a mediana do mês e nível. Lugar sem histórico de fogo nunca vira alerta por um foco isolado."""
    med = clim['median']
    if clim['p90'] <= 0:
        level = 'normal'
    elif value >= clim['p90']:
        level = 'critico'
    elif value >= clim['p75']:
        level = 'alto'
    elif value < clim['p25']:
        level = 'baixo'
    else:
        level = 'normal'
    return {**{k: round(clim[k], 2) for k in ('median', 'p75', 'p90')},
            'ratio': round(value / med, 2) if med > 0 else None, 'level': level}


def calendar(values: dict, lo: dict, hi: dict, sources: dict, years, baseline_years) -> list[dict]:
    """Matriz ano × mês completa (zeros incluídos), cada célula com valor, incerteza, climatologia e nível."""
    clim = climatology(values, baseline_years)
    out = []
    for y in years:
        for m in range(1, 13):
            v = values.get((y, m), 0.0)
            src = sources.get(y)
            out.append({'year': y, 'month': m, 'value': round(v, 2),
                        'lo': round(lo.get((y, m), v), 2), 'hi': round(hi.get((y, m), v), 2),
                        'source': src, 'estimated': src == 'AQUA', **assess(v, clim[m])})
    return out


def project(value_to_date: float, day: int, days_in_month: int) -> float:
    """Mês corrente: extrapola linearmente o acumulado até o fim do mês."""
    return value_to_date * days_in_month / day
