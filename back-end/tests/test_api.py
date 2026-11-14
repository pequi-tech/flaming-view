"""API de ponta a ponta com uma release mínima (contrato real) e FIRMS falso. Sem rede."""
import datetime as dt, json, os, tempfile, unittest
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app.api import create_app

YEARS = range(2010, 2014)
PANTANAL = '-58,-22,-54,-16'
CHUKOTKA = '170,60,-170,70'                       # cruza o antimeridiano


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


class Base(unittest.TestCase):
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


class TestArquivo(Base):
    def test_health(self):
        r = self.client.get('/health').json()
        self.assertEqual((r['status'], r['release'], r['years']), ('ok', 'v1', [2010, 2013]))

    def test_calendario(self):
        r = self.client.get('/calendar', params={'bbox': PANTANAL})
        self.assertEqual(r.status_code, 200)
        m = r.json()['months']
        self.assertEqual(len(m), 4 * 12)                                       # matriz completa
        aug = [x for x in m if x['month'] == 8]
        self.assertEqual([x['value'] for x in aug], [10, 20, 30, 40])
        self.assertEqual(aug[-1]['level'], 'critico')
        self.assertEqual(aug[0]['source'], 'AQUA')
        self.assertTrue(aug[0]['estimated'] and aug[0]['lo'] < 10 < aug[0]['hi'])
        self.assertEqual([x['value'] for x in m if x['month'] == 3], [0, 0, 0, 0])   # mês sem linha = zero
        self.assertIn('max-age', r.headers['cache-control'])

    def test_calendario_nao_vaza_celula_fora_da_caixa(self):
        m = self.client.get('/calendar', params={'bbox': '-58,-22,-56.05,-16'}).json()['months']
        self.assertEqual(sum(x['value'] for x in m), 0)                        # célula -56,0 começa fora

    def test_antimeridiano(self):
        m = self.client.get('/calendar', params={'bbox': CHUKOTKA}).json()['months']
        self.assertEqual({x['value'] for x in m if x['month'] == 7}, {12.0})   # 5 (lon 179) + 7 (lon -179)

    def test_recorte_de_anos(self):
        m = self.client.get('/calendar', params={'bbox': PANTANAL, 'from_year': 2012, 'to_year': 2013}).json()['months']
        self.assertEqual(sorted({x['year'] for x in m}), [2012, 2013])
        self.assertEqual(m[7]['median'], 25.0)                                 # base continua sendo todo o arquivo

    def test_csv(self):
        r = self.client.get('/calendar', params={'bbox': PANTANAL, 'format': 'csv'})
        self.assertTrue(r.headers['content-type'].startswith('text/csv'))
        lines = r.text.strip().splitlines()
        self.assertEqual(lines[0].split(',')[:4], ['year', 'month', 'value', 'lo'])
        self.assertEqual(len(lines), 49)

    def test_serie(self):
        y = self.client.get('/series', params={'bbox': PANTANAL}).json()['years']
        self.assertEqual([(r['year'], r['value']) for r in y], [(2010, 11), (2011, 21), (2012, 31), (2013, 41)])

    def test_celulas_para_o_globo(self):
        r = self.client.get('/cells', params={'year': 2013, 'month': 8, 'res': 1}).json()
        self.assertEqual(sorted((c['lat'], c['lon'], c['value']) for c in r['cells']), [(-19, -56, 40), (10, 10, 100)])
        r = self.client.get('/cells', params={'year': 2013, 'month': 8, 'res': 1, 'bbox': PANTANAL}).json()
        self.assertEqual(len(r['cells']), 1)

    def test_metodo(self):
        r = self.client.get('/method').json()
        self.assertEqual(r['metrics']['r2_cell2_month'], 0.96)
        self.assertEqual(r['contract_version'], '1.0.0')

    def test_validacao(self):
        for path, params in [('/calendar', {'bbox': '1,2,3'}), ('/calendar', {'bbox': PANTANAL, 'from_year': 1990}),
                             ('/calendar', {'bbox': PANTANAL, 'from_year': 2013, 'to_year': 2012}),
                             ('/calendar', {}), ('/cells', {'year': 2013, 'month': 13}), ('/cells', {'year': 2013, 'month': 8, 'res': 3})]:
            with self.subTest(path=path, params=params):
                self.assertEqual(self.client.get(path, params=params).status_code, 422)


class TestTempoReal(Base):
    def setUp(self):
        super().setUp()
        self.firms.rows = (nrt_row(-19.001, -56.001, '2014-08-02') + nrt_row(-19.002, -56.002, '2014-08-02')   # mesma célula-dia
                           + nrt_row(-19.001, -56.001, '2014-08-05') + nrt_row(-19.0, -56.0, '2014-08-06', conf='l'))  # baixa confiança sai

    def test_mes_corrente(self):
        r = self.client.get('/current', params={'bbox': PANTANAL}).json()
        self.assertEqual((r['year'], r['month'], r['day']), (2014, 8, 10))
        self.assertEqual(r['value_to_date'], 2)                               # 2 células-dia válidas
        self.assertAlmostEqual(r['projected'], 2 * 31 / 10, places=2)
        self.assertEqual(r['median'], 25.0)
        self.assertEqual(r['level'], 'baixo')
        self.assertFalse(r['stale'])
        self.assertEqual(len(self.firms.calls), 2)                            # dias 1-5 e 6-10
        self.assertTrue(all('TESTKEY' in u and 'VIIRS_NOAA21_NRT' in u for u in self.firms.calls))

    def test_cache_sqlite(self):
        self.client.get('/current', params={'bbox': PANTANAL})
        self.client.get('/current', params={'bbox': PANTANAL})
        self.assertEqual(len(self.firms.calls), 2)                            # segunda vez veio do cache
        other = self.make_client()                                            # outro processo, mesmo arquivo
        other.get('/current', params={'bbox': PANTANAL})
        self.assertEqual(len(self.firms.calls), 2)

    def test_janelas_fechadas_ficam_no_cache(self):
        """Dias 1-5 já não mudam no NRT: mesmo com TTL zero, só a janela recente (6-10) volta ao FIRMS."""
        self.client.get('/current', params={'bbox': PANTANAL})
        self.make_client(cache_ttl=0).get('/current', params={'bbox': PANTANAL})
        self.assertEqual(len(self.firms.calls), 3)
        self.assertTrue(self.firms.calls[-1].endswith('/5/2014-08-06'))

    def test_firms_fora_do_ar_usa_ultimo_snapshot(self):
        self.client.get('/current', params={'bbox': PANTANAL})
        self.firms.fail = True
        stale = self.make_client(cache_ttl=0).get('/current', params={'bbox': PANTANAL})
        self.assertEqual(stale.status_code, 200)
        self.assertTrue(stale.json()['stale'])
        self.assertEqual(stale.json()['value_to_date'], 2)

    def test_firms_fora_do_ar_sem_cache(self):
        self.firms.fail = True
        self.assertEqual(self.client.get('/current', params={'bbox': PANTANAL}).status_code, 503)

    def test_sem_chave(self):
        self.assertEqual(self.make_client(map_key=None).get('/current', params={'bbox': PANTANAL}).status_code, 503)

    def test_antimeridiano_vira_duas_consultas(self):
        self.client.get('/current', params={'bbox': CHUKOTKA})
        areas = {u.split('/')[-3] for u in self.firms.calls}
        self.assertEqual(areas, {'170,60,180,70', '-180,60,-170,70'})


class TestRelease(unittest.TestCase):
    def test_release_corrompida_nao_sobe(self):
        with tempfile.TemporaryDirectory() as t:
            make_release(t)
            with open(os.path.join(t, 'v1', 'grid', 'year=2012.parquet'), 'ab') as f:
                f.write(b'x')
            with self.assertRaises(RuntimeError):
                create_app(release_dir=t, cache_path=os.path.join(t, 'c.db'))

    def test_contrato_incompativel_nao_sobe(self):
        with tempfile.TemporaryDirectory() as t:
            make_release(t)
            m = json.loads(Path(t, 'v1', 'manifest.json').read_text())
            Path(t, 'v1', 'manifest.json').write_text(json.dumps({**m, 'contract_version': '2.0.0'}))
            with self.assertRaises(RuntimeError):
                create_app(release_dir=t, cache_path=os.path.join(t, 'c.db'))


if __name__ == '__main__':
    unittest.main()
