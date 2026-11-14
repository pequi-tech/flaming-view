"""/health, /method e as recusas de boot da release."""
import json, os, tempfile, unittest
from pathlib import Path
from app.main import create_app
from tests.fixtures import ApiCase, make_release


class TestSystemRoutes(ApiCase):
    def test_health(self):
            r = self.client.get('/health').json()
            self.assertEqual((r['status'], r['release'], r['years']), ('ok', 'v1', [2010, 2013]))

    def test_metodo(self):
            r = self.client.get('/method').json()
            self.assertEqual(r['metrics']['r2_cell2_month'], 0.96)
            self.assertEqual(r['contract_version'], '1.0.0')


class TestReleaseBoot(unittest.TestCase):
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
