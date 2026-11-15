"""API sobre a release real (serving/release). Fatos conhecidos e metas de latência. Pula se a release não existir."""
import os, tempfile, time, unittest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import create_app

REL = os.environ.get('FV_RELEASE', str(Path(__file__).resolve().parents[3] / 'serving' / 'release'))
MAX_MS = 500                                         # meta por requisição sem cache, numa máquina de dev


@unittest.skipUnless(Path(REL, 'CURRENT').exists(), 'sem release: rode `make publish` em serving/')
class TestReleaseReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.c = TestClient(create_app(release_dir=REL, cache_path=os.path.join(cls.tmp.name, 'c.db'), map_key=''))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def timed(self, path, **params):
        t = time.perf_counter()
        r = self.c.get(path, params=params)
        ms = (time.perf_counter() - t) * 1000
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertLess(ms, MAX_MS, f'{path} {params} levou {ms:.0f} ms')
        return r.json()

    def month(self, bbox, year, m):
        return next(x for x in self.timed('/calendar', bbox=bbox)['months'] if (x['year'], x['month']) == (year, m))

    def test_eventos_conhecidos_sao_criticos(self):
        for name, bbox, y, m in [('Pantanal jun/2024', '-58,-22,-54,-16', 2024, 6),
                                 ('Black Summer dez/2019', '145,-38,154,-28', 2019, 12),
                                 ('Quebec jun/2023', '-80,48,-60,56', 2023, 6)]:
            with self.subTest(name):
                x = self.month(bbox, y, m)
                self.assertEqual(x['level'], 'critico')
                self.assertGreater(x['ratio'], 5)

    def test_antimeridiano_russia_oriental(self):
        self.assertGreater(sum(x['value'] for x in self.timed('/calendar', bbox='160,55,-170,72')['months']), 0)

    def test_mundo_inteiro_e_rapido(self):
        y = self.timed('/series', bbox='-180,-90,180,90')['years']
        self.assertEqual([r['year'] for r in y][:23], list(range(2003, 2026)))   # 2026 parcial (Brasil) pode vir junto
        self.assertTrue(all(r['value'] > 0 for r in y))

    def test_globo(self):
        for res in (2, 1, 0.5, 0.25):
            with self.subTest(res=res):
                self.assertGreater(len(self.timed('/cells', year=2024, month=8, res=res)['cells']), 100)

    def test_metodo(self):
        self.assertLessEqual(self.timed('/method')['metrics']['mape_total_monthly_pct'], 10)


if __name__ == '__main__':
    unittest.main()


BRAZIL = '-74,-34,-34,6'


@unittest.skipUnless(Path(REL, 'CURRENT').exists(), 'sem release: rode `make publish` em serving/')
class TestPrevisaoReal(unittest.TestCase):
    """RNF-01 e aceites do contrato 1.1 sobre a release real."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.c = TestClient(create_app(release_dir=REL, cache_path=os.path.join(cls.tmp.name, 'c.db'), map_key=''))
        if not cls.c.get('/method').json().get('model'):
            raise unittest.SkipTest('release sem previsão')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def timed(self, path, max_ms, **params):
        t = time.perf_counter()
        r = self.c.get(path, params=params)
        ms = (time.perf_counter() - t) * 1000
        self.assertEqual(r.status_code, 200, r.text[:300])
        self.assertLess(ms, max_ms, f'{path} {params} levou {ms:.0f} ms')
        return r.json()

    def test_forecast_rio_verde(self):
        r = self.timed('/forecast', 300, area_id='BR5218805', horizon=1)
        h = r['horizons'][0]
        self.assertEqual(sum(h['classes'].values()), h['cells'])
        self.assertGreater(h['cells'], 200)

    def test_hexagonos_ipp_brasil_e_soma(self):
        self.c.get('/cells', params={'layer': 'ipp', 'horizon': 2, 'shape': 'h3', 'h3_res': 5, 'bbox': BRAZIL})  # aquece o DuckDB
        self.timed('/cells', 500, layer='ipp', horizon=1, shape='h3', h3_res=5, bbox=BRAZIL)
        sq = self.c.get('/cells', params={'layer': 'forecast', 'horizon': 1, 'area_id': 'BR52'}).json()
        hx = self.c.get('/cells', params={'layer': 'forecast', 'horizon': 1, 'area_id': 'BR52', 'shape': 'h3', 'h3_res': 5}).json()
        a, b = sum(c['value'] for c in sq['cells']), sum(c['value'] for c in hx['cells'])
        self.assertLess(abs(a - b) / max(b, 1e-9), 0.01)   # quadrado omite células ~0 previstas

    def test_celula_e_prioridades(self):
        p = self.timed('/priorities', 400, area_id='BR52', horizon=1)
        self.assertEqual(p['granularity'], 'municipality')
        cell = self.timed('/priorities', 400, area_id='BR5218805')['items'][0]['id']
        self.timed(f'/cell/{cell}', 200)
        self.assertEqual(self.timed('/priorities', 400, area_id='USA')['granularity'], 'hexagon')

    def test_busca(self):
        r = self.timed('/areas', 200, q='rio ver')
        self.assertIn('BR5218805', [a['area_id'] for a in r['areas'][:3]])
        self.assertLess(len(self.c.get('/areas/BR5218805/geometry').content), 50_000)
