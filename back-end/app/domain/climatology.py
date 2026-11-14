"""Climatologia do mês e classificação: quão fora do normal está um valor."""
import numpy as np

LEVELS = ('baixo', 'normal', 'alto', 'critico')


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
