"""Motor de recomendações (RF-API-05): oito regras puras. Decide quais ações sugerir; o texto vem do front por `key`.

Classes como ordinal: 0 baixo < 1 normal < 2 alto < 3 critico. Contexto de célula ou de município
(no município, cada condição vale se valer para qualquer célula; `crit_share` só existe no município, R7).
"""
from .ipp_params import EXPOSED, RECURRENT

ORDER = ('baixo', 'normal', 'alto', 'critico')
RULES = {   # id: (decisões, severidade)
    'R1': (['D1', 'D5'], 'high'), 'R2': (['D2'], 'medium'), 'R3': (['D2', 'D3'], 'medium'), 'R4': (['D3'], 'medium'),
    'R5': (['D4'], 'low'), 'R6': (['D3'], 'low'), 'R7': (['D4'], 'high'), 'R8': (['D1', 'D5'], 'high'),
}
SEVERITY = {'high': 0, 'medium': 1, 'low': 2}
ACTION_RANK = {'R8': 0, 'R7': 1, 'R1': 2, 'R2': 3, 'R3': 3, 'R4': 3, 'R5': 4, 'R6': 4}   # D-01: ação mais grave primeiro
NO_ACTION = 5
RAIN_DRY = -0.30
CRIT_SHARE = 0.20


def cell_context(k: list[int], e: float, e_ti: float, v: float, rain_anomaly=None, current_level=None) -> dict:
    """Contexto de uma célula: k = classes previstas [M+1, M+2, M+3] como ordinal."""
    return {'k': k, 'exposed_high': k[0] >= 2 and e >= EXPOSED, 'ti_critical': e_ti >= 1 and max(k) == 3,
            'recurrent_normal': v >= RECURRENT and k[0] == 1, 'rain_anomaly': rain_anomaly,
            'crit_share': None, 'current_level': current_level}


def recommend(ctx: dict) -> list[dict]:
    k = ctx['k']
    hit = {
        'R1': k[0] == 3,
        'R2': ctx['exposed_high'],
        'R3': ctx['ti_critical'],
        'R4': ctx.get('rain_anomaly') is not None and ctx['rain_anomaly'] <= RAIN_DRY,
        'R5': k[2] > k[0],
        'R6': ctx['recurrent_normal'],
        'R7': ctx.get('crit_share') is not None and ctx['crit_share'] >= CRIT_SHARE,
        'R8': ctx.get('current_level') == 'critico',
    }
    out = [{'rule_id': r, 'decisions': RULES[r][0], 'severity': RULES[r][1], 'key': f'rec.{r}'} for r, ok in hit.items() if ok]
    return sorted(out, key=lambda x: (SEVERITY[x['severity']], int(x['rule_id'][1:])))


def action_rank(recs: list[dict]) -> int:
    """Gravidade da ação mais grave de uma unidade (0 = R8 … 4 = R5/R6, 5 = nenhuma). Ordena o plano (D-01)."""
    return min((ACTION_RANK[r['rule_id']] for r in recs), default=NO_ACTION)
