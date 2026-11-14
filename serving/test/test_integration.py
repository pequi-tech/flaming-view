"""Release publicada a partir dos dados reais: contrato, checksums e o que o back-end vai ler.
Pula se ainda não houve `make publish` (release/CURRENT)."""
import glob, os, sys, unittest
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import publish as pb

REL = os.environ.get('RELEASE', os.path.join(os.path.dirname(__file__), '..', 'release'))
CUR = Path(REL, 'CURRENT')


@unittest.skipUnless(CUR.exists(), 'rode `make publish` em serving/')
class TestRelease(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = os.path.join(REL, CUR.read_text().strip())
        cls.files = sorted(glob.glob(os.path.join(cls.path, 'grid', 'year=*.parquet')))

    def test_checksums_e_contrato(self):
        self.assertEqual(pb.verify(self.path), [])

    def test_cada_ano_cumpre_o_contrato(self):
        for p in self.files:
            year = int(p.split('year=')[1][:4])
            with self.subTest(year=year):
                g = pd.read_parquet(p)
                self.assertEqual(pb.check_grid(g, year), [])          # tipos sobrevivem ao round-trip do Parquet

    def test_factors(self):
        self.assertEqual(pb.check_columns(pd.read_parquet(os.path.join(self.path, 'factors.parquet')), pb.FACTORS), [])

    def test_leitura_por_bbox_como_o_back_end(self):
        """Filtro de bbox por estatística de row group: Pantanal, junho/2024 ~ 12x a mediana de junho."""
        f = [('lat', '>=', -22.0), ('lat', '<=', -16.0), ('lon', '>=', -58.0), ('lon', '<=', -54.0), ('month', '==', 6)]
        g = pd.concat(pd.read_parquet(p, columns=['year', 'activity'], filters=f) for p in self.files)
        jun = g.groupby('year').activity.sum()
        self.assertGreater(jun[2024] / jun.drop(2024).median(), 8)

    def test_sem_antartida(self):
        g = pd.read_parquet(self.files[-1], columns=['lat'])
        self.assertGreaterEqual(g.lat.min(), -60.0)


if __name__ == '__main__':
    unittest.main()
