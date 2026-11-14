"""Release mínima com o contrato real e FIRMS falso: base dos testes de API, sem rede."""
import datetime as dt, json, os, tempfile, unittest
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.main import create_app

YEARS = range(2010, 2014)
PANTANAL = '-58,-22,-54,-16'
CHUKOTKA = '170,60,-170,70'


def cell_id(lat, lon):
    return int((round(lat * 20) + 1800) * 7200 + (round(lon * 20) + 3600))


def grid_year(year):
    """Agosto no Pantanal: 10, 20, 30, 40 por ano; janeiro 1; uma célula de cada lado do antimeridiano."""
    rows = [(-19.0, -56.0, 8, 10.0 * (year - 2009)), (-19.0, -56.0, 1, 1.0),
            (65.0, 179.0, 7, 5.0), (65.0, -179.0, 7, 7.0), (10.0, 10.0, 8, 100.0)]
    src = 'AQUA' if year <= 2011 else 'SNPP'
    d = pd.DataFrame(rows, columns=['lat', 'lon', 'month', 'activity'])
    factor = 0.25 if src == 'AQUA' else 1.0
    return pd.DataFrame({
        'cell_id': np.array([cell_id(a, b) for a, b in zip(d.lat, d.lon)], dtype='int32'),
        'lat': d.lat, 'lon': d.lon, 'year': np.int16(year), 'month': d.month.astype('int8'),
        'source': pd.Categorical([src] * len(d), categories=['AQUA', 'SNPP', 'N20']),
        'detections': np.int32(100), 'cell_days': (d.activity * factor).astype('int32'),
        'factor': np.float32(factor), 'factor_level': pd.Categorical(['observed' if src == 'SNPP' else 'c2'] * len(d),
                                                                      categories=['observed', 'c2', 'c10', 'band', 'global']),
        'activity': d.activity.astype('float32'),
        'activity_lo': (d.activity * (0.8 if src == 'AQUA' else 1)).astype('float32'),
        'activity_hi': (d.activity * (1.3 if src == 'AQUA' else 1)).astype('float32'),
    }).sort_values(['cell_id', 'month'])


def make_release(root):
    v = Path(root, 'v1')
    (v / 'grid').mkdir(parents=True)
    files = {}
    for y in YEARS:
        p = v / 'grid' / f'year={y}.parquet'
        grid_year(y).to_parquet(p, index=False)
        files[f'grid/year={y}.parquet'] = {'bytes': p.stat().st_size}
    metrics = {'mape_total_monthly_pct': 4.7, 'r2_cell2_month': 0.96, 'level_share': {'c2': 0.98}}
    (v / 'metrics.json').write_text(json.dumps(metrics))
    (v / 'manifest.json').write_text(json.dumps({'version': 'v1', 'contract_version': '1.0.0', 'years': [YEARS[0], YEARS[-1]],
                                                  'rows': 20, 'quality': {'metrics': metrics}, 'files': files}))
    Path(root, 'CURRENT').write_text('v1\n')


NRT_HEADER = 'latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n'


def nrt_row(lat, lon, date, conf='n'):
    return f'{lat},{lon},330,0.4,0.4,{date},1700,N21,VIIRS,{conf},2.0NRT,290,5,D\n'


class FakeFirms:
    """Responde como a API de área do FIRMS e conta as chamadas."""
    def __init__(self, rows='', fail=False):
        self.rows, self.fail, self.calls = rows, fail, []

    def __call__(self, url):
        self.calls.append(url)
        if self.fail:
            raise OSError('FIRMS fora do ar')
        return NRT_HEADER + self.rows


class ApiCase(unittest.TestCase):
    """Cliente da API com release sintética, cache SQLite temporário e FIRMS falso. Hoje = 10/08/2014."""
    TODAY = dt.date(2014, 8, 10)                    # mês corrente: agosto/2014, 10 de 31 dias

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        make_release(os.path.join(self.tmp.name, 'release'))
        self.firms = FakeFirms()
        self.client = self.make_client()

    def make_client(self, **kw):
        args = dict(release_dir=os.path.join(self.tmp.name, 'release'), cache_path=os.path.join(self.tmp.name, 'cache.db'),
                    map_key='TESTKEY', fetch=self.firms, today=lambda: self.TODAY)
        return TestClient(create_app(**{**args, **kw}))

    def tearDown(self):
        self.tmp.cleanup()
