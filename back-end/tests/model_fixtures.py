"""Release sintética com previsão, território e áreas (contrato 1.1): duas células em Rio Verde-GO, uma em TI."""
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

from tests.fixtures import ApiCase, cell_id, make_release

RV = 'BR5218805'
CELLS = [  # lat, lon, mun, v, e_pop, e_ti, ti, classes M+1..3, predicted
    (-19.0, -56.0, '5218805', 0.9, 0.8, 0.0, None, ('critico', 'alto', 'critico'), 30.0),
    (-19.05, -56.0, '5218805', 0.3, 0.1, 1.0, 'TI Teste', ('normal', 'normal', 'critico'), 2.0),
]


def make_model_release(root):
    make_release(root)
    v = Path(root, 'v1')
    ids = np.array([cell_id(a, b) for a, b, *_ in CELLS], 'int32')
    t = pd.DataFrame({'cell_id': ids, 'lat': [c[0] for c in CELLS], 'lon': [c[1] for c in CELLS],
                      'v': np.float32([c[3] for c in CELLS]), 'e_pop': np.float32([c[4] for c in CELLS]),
                      'e_ti': np.float32([c[5] for c in CELLS]),
                      'e': np.float32([max(c[4], 0.8 * c[5]) for c in CELLS]), 'ti_name': [c[6] for c in CELLS],
                      'municipality_id': [c[2] for c in CELLS], 'state_id': ['52', '52'], 'country': ['BRA', 'BRA'],
                      'h3_4': ['h4a', 'h4a'], 'h3_5': ['h5a', 'h5a'], 'h3_6': ['h6a', 'h6b']})
    rows = [(i, h, f'2014-{8 + h:02d}', c[7][h - 1], c[8] / h, c[8] / h / 2, c[8] / h * 2, 2.0 / h, 0.9 / h)
            for i, c in zip(ids, CELLS) for h in (1, 2, 3)]
    p = pd.DataFrame(rows, columns=['cell_id', 'horizon', 'forecast_month', 'class', 'predicted', 'lo', 'hi', 'ratio', 'n'])
    p = p.assign(horizon=p.horizon.astype('int8'), recent_data=True, model_version='rf-test', generated_at='2014-08-01')
    a = pd.DataFrame([('BRA', 'country', 'Brasil', None, -74, -34, -34, 6, None),
                      ('BR52', 'state', 'Goiás', 'BRA', -54, -20, -45, -12, None),
                      (RV, 'municipality', 'Rio Verde - GO', 'BR52', -56.1, -19.2, -55.9, -18.9, 238025.0)],
                     columns=['area_id', 'level', 'name', 'parent_id', 'w', 's', 'e', 'n', 'population'])
    a['search'] = a.name.str.lower().str.replace('á', 'a')
    t.to_parquet(v / 'territory.parquet'); p.to_parquet(v / 'predictions.parquet'); a.to_parquet(v / 'areas.parquet')
    imp = {'features': ['a_t', 'oni'], 'importances': [0.6, 0.1]}
    metrics = {'model_version': 'rf-test', 'issue_month': '2013-12', 'oni_recent': 1.2,
               'horizons': {str(h): {'auc': 0.7, 'top10_precision': 0.33, 'base_rate': 0.14, **imp} for h in (1, 2, 3)}}
    (v / 'model_metrics.json').write_text(json.dumps(metrics))
    (v / 'areas').mkdir()
    sq = {'type': 'Polygon', 'coordinates': [[[-56.1, -19.2], [-55.9, -19.2], [-55.9, -18.9], [-56.1, -19.2]]]}
    (v / 'areas' / 'municipalities.geojson').write_text(json.dumps(
        {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'area_id': RV}, 'geometry': sq}]}))
    m = json.loads((v / 'manifest.json').read_text())
    for f in ('territory.parquet', 'predictions.parquet', 'areas.parquet', 'model_metrics.json'):
        m['files'][f] = {'bytes': (v / f).stat().st_size}
    m['contract_version'] = '1.1.0'
    (v / 'manifest.json').write_text(json.dumps(m))
    return [int(i) for i in ids]


class FakeLlm:
    available = True

    def __init__(self):
        self.calls = []

    def stream(self, system, messages):
        self.calls.append((system, messages))
        yield 'Olá '
        yield 'mundo'


class ModelApiCase(ApiCase):
    def setUp(self):
        super().setUp()
        self.tmp.cleanup()
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.ids = make_model_release(os.path.join(self.tmp.name, 'release'))
        self.llm = FakeLlm()
        self.client = self.make_client(llm=self.llm)
