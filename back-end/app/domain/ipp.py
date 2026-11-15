"""Índice de Prioridade Preventiva: média geométrica ponderada de previsão (N), histórico (V) e exposição (E).
Ordena atenção; não é probabilidade de desastre."""
from .ipp_params import CUT_QUANTILES, FLOOR, IPP_LEVELS, WEIGHTS

NAMES = ('n', 'v', 'e')


def ipp(n: float, v: float, e: float) -> float:
    c = {'n': n, 'v': v, 'e': e}
    out = 1.0
    for k, w in WEIGHTS.items():
        out *= max(FLOOR, min(1.0, c[k])) ** w
    return out


def ipp_level(value: float, cuts: dict) -> str:
    """cuts = {'medio': p50, 'alto': p75, 'critico': p90} globais da release."""
    level = 'baixo'
    for name in ('medio', 'alto', 'critico'):
        if value >= cuts[name]:
            level = name
    return level


def explain(n: float, v: float, e: float) -> dict:
    """Os dois componentes que mais puxam o índice para cima e o mais fraco. O texto vem do dicionário do front."""
    order = sorted(NAMES, key=lambda k: -{'n': n, 'v': v, 'e': e}[k])
    return {'dominant': order[:2], 'weak': order[2]}


assert set(CUT_QUANTILES) == set(IPP_LEVELS[1:])
