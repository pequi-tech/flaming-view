"""Calendário do fogo: matriz ano × mês completa, cada mês classificado contra a própria climatologia."""
from .climatology import assess, climatology


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


def yearly_totals(values: dict, lo: dict, hi: dict, sources: dict, years) -> list[dict]:
    """Total por ano, com faixa de incerteza e sensor."""
    tot = lambda d, y: round(sum(v for (yy, _), v in d.items() if yy == y), 2)
    return [{'year': y, 'value': tot(values, y), 'lo': tot(lo, y), 'hi': tot(hi, y), 'source': sources.get(y)} for y in years]
