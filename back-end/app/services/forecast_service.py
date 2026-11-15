"""Casos de uso da previsão: resumo por área (RF-API-01) e camadas do mapa previsão/IPP/histórico em hexágonos (RF-API-02)."""
from ..domain.climatology import LEVELS, assess, climatology
from ..domain.ipp import ipp_level
from ..domain.territory import Area, bbox_filter
from ..domain.units import UNIT
from ..infra.model_store import ModelStore
from ..infra.release import Release

METRIC_KEYS = ('auc', 'top10_precision', 'base_rate', 'mae', 'mae_baseline', 'gain', 'resolution_used')


def ym(text: str) -> tuple[int, int]:
    y, m = text.split('-')
    return int(y), int(m)


class ForecastService:
    def __init__(self, release: Release, store: ModelStore):
        self.release, self.store = release, store

    def metrics(self, h: int) -> dict:
        m = self.release.model_metrics.get('horizons', {}).get(str(h), {})
        return {k: m.get(k) for k in METRIC_KEYS}

    def area_history(self, area: Area):
        """Série mensal da área: células da área administrativa, ou a caixa."""
        flt = None if area.level == 'bbox' else area.cell_filter()
        return self.release.monthly(area.bbox, flt)[0]

    def forecast(self, area: Area, horizons=(1, 2, 3)) -> dict:
        where, params = area.cell_filter()
        val = self.area_history(area)
        clim = climatology(val, self.release.baseline_years)
        out, recent, version = [], True, self.release.model_metrics.get('model_version')
        for h in horizons:
            rows = self.store.forecast(where, params, h)
            classes = {lv: 0 for lv in LEVELS}
            for r in rows:
                classes[r['level']] = r['cells']
            total = sum(r['predicted'] for r in rows)
            month = rows[0]['forecast_month'] if rows else None
            recent = recent and all(r['recent'] for r in rows)
            y, m = ym(month) if month else (None, None)
            a = assess(total, clim[m]) if m else {'median': 0, 'p75': 0, 'p90': 0, 'ratio': None, 'level': 'normal'}
            out.append({'horizon': h, 'forecast_month': month, 'classes': classes, 'cells': sum(classes.values()),
                        'predicted': round(total, 2), 'lo': round(sum(r['lo'] for r in rows), 2),
                        'hi': round(sum(r['hi'] for r in rows), 2), **a,
                        'last_year': round(val.get((y - 1, m), 0.0), 2) if m else None, 'metrics': self.metrics(h)})
        return {'area': {'id': area.id, 'name': area.name, 'level': area.level}, 'unit': UNIT, 'release': self.release.version,
                'model_version': version, 'issue_month': self.release.model_metrics.get('issue_month'),
                'recent_data': recent, 'horizons': out}

    def cells(self, layer: str, h: int, h3_res: int | None, area: Area | None, bbox, year=None, month=None) -> dict:
        where, params = area.cell_filter() if area else bbox_filter(bbox) if bbox else ('TRUE', [])
        if layer == 'history':
            rows = self.store.history_h3(where, params, year, month, h3_res)
        else:
            rows = self.store.cells(where, params, h, layer, h3_res)
        cuts = self.store.cuts.get(h, {})
        level = (lambda r: ipp_level(r['value'], cuts)) if layer == 'ipp' else \
                (lambda r: None) if layer == 'history' else (lambda r: LEVELS[int(r['k'])])
        return {'layer': layer, 'horizon': h, 'shape': 'h3' if h3_res else 'square', 'h3_res': h3_res,
                'unit': 'IPP' if layer == 'ipp' else UNIT, 'release': self.release.version, 'cuts': cuts if layer == 'ipp' else None,
                'cells': [{'id': r['id'], 'lat': round(r['lat'], 4), 'lon': round(r['lon'], 4),
                           'value': round(float(r['value']), 4), 'level': level(r)} for r in rows]}
