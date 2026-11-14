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
        self.assertEqual(len(y), 23)
        self.assertTrue(all(r['value'] > 0 for r in y))

    def test_globo(self):
        for res in (2, 1, 0.5, 0.25):
            with self.subTest(res=res):
                self.assertGreater(len(self.timed('/cells', year=2024, month=8, res=res)['cells']), 100)

    def test_metodo(self):
        self.assertLessEqual(self.timed('/method')['metrics']['mape_total_monthly_pct'], 10)


if __name__ == '__main__':
    unittest.main()
