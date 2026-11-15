"""Casos de uso do território: detalhe da célula (RF-API-03) e lista de prioridades com recomendações (RF-API-04/05)."""
from ..domain.area import BBox
from ..domain.climatology import LEVELS, assess, climatology
from ..domain.ipp import explain, ipp_level
from ..domain.recommendations import action_rank, cell_context, recommend
from ..domain.territory import Area
from ..infra.model_store import ModelStore
from ..infra.release import Release
from .forecast_service import ym

LAG_FEATURES = ('a_t', 'a_t1', 'a_t2', 'ma3', 'ma12', 'a_T12')


class TerritoryService:
    def __init__(self, release: Release, store: ModelStore):
        self.release, self.store = release, store

    def _ipp(self, h, n, v, e, ipp):
        return {'value': round(ipp, 4), 'level': ipp_level(ipp, self.store.cuts[h]), 'n': round(n, 3), 'v': round(v, 3),
                'e': round(e, 3), 'explanation': explain(n, v, e)}

    def drivers(self, val: dict, clim: dict, issue: tuple[int, int]) -> list[dict]:
        """Fatores: atividade recente vs. mediana e ONI, com a importância no modelo M+1. POWER: fora desta versão."""
        m = self.release.model_metrics.get('horizons', {}).get('1', {})
        imp = dict(zip(m.get('features', []), m.get('importances', [])))
        t = issue[0] * 12 + issue[1] - 1
        last3 = [((t - k) // 12, (t - k) % 12 + 1) for k in range(3)]
        act, med = sum(val.get(p, 0.0) for p in last3), sum(clim[p[1]]['median'] for p in last3)
        oni = self.release.model_metrics.get('oni_recent')
        return [
            {'key': 'activity', 'value': round(act / med - 1, 3) if med > 0 else None, 'unit': 'ratio',
             'importance': round(sum(imp.get(k, 0) for k in LAG_FEATURES), 3), 'available': True},
            {'key': 'oni', 'value': oni, 'unit': '°C', 'importance': round(imp.get('oni', 0) + imp.get('oni3', 0), 3),
             'available': oni is not None},
            *({'key': k, 'value': None, 'unit': u, 'importance': None, 'available': False}
              for k, u in (('rain', '%'), ('temperature', '°C'), ('humidity', 'p.p.'), ('wind', '%'))),
        ]

    def cell(self, cell_id: int) -> dict:
        r = self.store.cell(cell_id)
        names = self.store.names([x for x in (r['country'], r['state_id'] and 'BR' + r['state_id'],
                                               r['municipality_id'] and 'BR' + r['municipality_id']) if x])
        box = BBox(r['lon'], r['lat'], r['lon'] + 0.05, r['lat'] + 0.05)
        val = self.release.monthly(box, ('cell_id = ?', [cell_id]))[0]
        clim = climatology(val, self.release.baseline_years)
        mm = self.release.model_metrics
        issue = ym(mm['issue_month'] if r['recent'] else mm.get('issue_month_outside_partial', mm['issue_month']))
        t = issue[0] * 12 + issue[1] - 1
        months = [((t - k) // 12, (t - k) % 12 + 1) for k in range(23, -1, -1)]
        history = [{'year': y, 'month': m, 'value': round(val.get((y, m), 0.0), 2), **assess(val.get((y, m), 0.0), clim[m])}
                   for y, m in months]
        k = [r['k1'], r['k2'], r['k3']]
        return {
            'cell_id': cell_id, 'lat': r['lat'], 'lon': r['lon'], 'release': self.release.version,
            'model_version': r['model_version'], 'recent_data': r['recent'], 'issue_month': f'{issue[0]}-{issue[1]:02d}',
            'place': {'country': r['country'], 'country_name': names.get(r['country']),
                      'state_id': r['state_id'] and 'BR' + r['state_id'], 'state_name': names.get(r['state_id'] and 'BR' + r['state_id']),
                      'municipality_id': r['municipality_id'] and 'BR' + r['municipality_id'],
                      'municipality_name': names.get(r['municipality_id'] and 'BR' + r['municipality_id']), 'ti_name': r['ti_name']},
            'exposure': {'v': round(r['v'], 3), 'e': round(r['e'], 3), 'e_pop': round(r['e_pop'], 3), 'e_ti': r['e_ti']},
            'forecast': [{'horizon': h, 'forecast_month': r[f'm{h}'], 'level': r[f'c{h}'], 'predicted': round(r[f'p{h}'], 2),
                          'lo': round(r[f'lo{h}'], 2), 'hi': round(r[f'hi{h}'], 2), 'ratio': round(r[f'r{h}'], 3),
                          'ipp': self._ipp(h, r[f'n{h}'], r['v'], r['e'], r[f'ipp{h}'])} for h in (1, 2, 3)],
            'history': history, 'climatology': [{'month': m, **{q: round(clim[m][q], 2) for q in ('p25', 'median', 'p75', 'p90')}}
                                                for m in range(1, 13)],
            'drivers': self.drivers(val, clim, issue),
            'recommendations': recommend(cell_context(k, r['e'], r['e_ti'], r['v'])),
        }

    SORTS = {'action': lambda i: (action_rank(i['recommendations']), -i['predicted'], -i['ipp']),   # D-01
             'fire': lambda i: (-i['predicted'], -i['ipp']), 'ipp': lambda i: (-i['ipp'], -i['predicted'])}

    def priorities(self, area: Area, h: int, limit: int, sort: str = 'action') -> dict:
        where, params = area.cell_filter()
        kind = ('municipality' if area.level in ('state', 'country') and area.in_brazil else
                'cell' if area.level == 'municipality' else 'hexagon')
        key = {'municipality': 'municipality_id', 'cell': 'cell_id', 'hexagon': 'h3_5'}[kind]
        rows = self.store.priorities(where, params, h, key)
        names = self.store.names(['BR' + r['id'] for r in rows]) if kind == 'municipality' else {}
        items = []
        for r in rows:
            ctx = {'k': [r['k1'], r['k2'], r['k3']], 'exposed_high': r['exposed_high'], 'ti_critical': r['ti_critical'],
                   'recurrent_normal': r['recurrent_normal'], 'rain_anomaly': None, 'current_level': None,
                   'crit_share': r['crit_share'] if kind == 'municipality' else None}
            items.append({'id': 'BR' + r['id'] if kind == 'municipality' else r['id'], 'kind': kind,
                          'name': names.get('BR' + r['id']) if kind == 'municipality' else None,
                          **self._ipp(h, r['n'], r['v'], r['e'], r['ipp']), 'ipp': round(r['ipp'], 4),
                          'forecast_level': LEVELS[r[f'k{h}']], 'predicted': round(r['predicted'], 2), 'cells': r['cells'],
                          'critical_cells': r['critical'], 'ti_name': r['ti_name'], 'lat': round(r['lat'], 4), 'lon': round(r['lon'], 4),
                          'recommendations': recommend(ctx)})
        items = sorted(items, key=self.SORTS[sort])
        return {'area': {'id': area.id, 'name': area.name, 'level': area.level}, 'horizon': h, 'granularity': kind,
                'sort': sort, 'total': len(items),
                'release': self.release.version, 'cuts': self.store.cuts[h], 'items': items[:limit]}
