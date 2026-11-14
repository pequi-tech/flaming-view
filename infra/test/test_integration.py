"""Metas de acurácia sobre os dados reais. Pula se `data/grid/` ainda não foi gerado (`make`).
Fatos regionais pulam se a região não estiver nos dados (ex.: rodou só um país)."""
import glob, json, os, unittest
import pandas as pd

D = os.environ.get('DATA', os.path.join(os.path.dirname(__file__), '..', 'data'))
HAVE = os.path.exists(os.path.join(D, 'metrics.json')) and glob.glob(os.path.join(D, 'grid', '*.parquet'))


def grid(cols, bbox=None, years=None):
    """Lê só as colunas e a caixa pedidas (W, S, E, N)."""
    f = []
    if bbox:
        w, s, e, n = bbox
        f = [('lon05', '>=', w), ('lon05', '<=', e), ('lat05', '>=', s), ('lat05', '<=', n)]
    files = sorted(glob.glob(os.path.join(D, 'grid', '*.parquet')))
    if years:
        files = [p for p in files if int(os.path.basename(p)[:4]) in years]
    return pd.concat(pd.read_parquet(p, columns=cols, filters=f or None) for p in files)


@unittest.skipUnless(HAVE, 'rode `make` em infra/ para gerar data/')
class TestAccuracy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.loads(open(os.path.join(D, 'metrics.json')).read())
        cls.f = pd.read_csv(os.path.join(D, 'factors.csv'))

    def test_metas_de_validacao(self):
        self.assertLessEqual(self.m['mape_total_monthly_pct'], 10.0)
        self.assertGreaterEqual(self.m['r2_cell2_month'], 0.90)
        self.assertGreaterEqual(self.m['n_cell2_months'], 500)
        self.assertGreaterEqual(self.m['level_share'].get('c2', 0), 0.7)   # a maioria das células tem fator próprio

    def test_fator_na_faixa_fisica(self):
        k = self.f[(self.f.link == 'AQUA_SNPP') & (self.f.level == 'c2')]
        self.assertTrue(0.15 < k.factor.median() < 0.35)           # VIIRS vê 3-6x mais células-dia que o Aqua
        g = self.f[(self.f.link == 'AQUA_SNPP') & (self.f.level == 'global')]
        self.assertEqual(len(g), 12)                                 # todo mês tem fator de último recurso
        n20 = self.f[(self.f.link == 'N20_SNPP') & (self.f.level == 'global')]
        self.assertTrue(0.9 < n20.factor.median() < 1.1)           # mesmo sensor, mesmo plano orbital

    def test_serie_sem_degrau_na_troca_de_sensor(self):
        y = grid(['year', 'viirs_eq'], years=range(2009, 2015)).groupby('year').viirs_eq.sum()
        self.assertLess(abs(y.loc[2012:2014].mean() / y.loc[2009:2011].mean() - 1), 0.5)   # sem harmonizar daria ~4x

    def _extreme(self, bbox, year, month, min_ratio):
        g = grid(['year', 'month', 'viirs_eq'], bbox=bbox)
        g = g[g.month == month].groupby('year').viirs_eq.sum()
        if year not in g or g.drop(year).median() == 0:
            self.skipTest('região fora dos dados')
        self.assertGreater(g[year] / g.drop(year).median(), min_ratio)

    def test_pantanal_junho_2024(self):
        self._extreme((-58, -22, -54, -16), 2024, 6, 8)

    def test_australia_black_summer_dez_2019(self):
        self._extreme((145, -38, 154, -28), 2019, 12, 5)            # NSW/Victoria

    def test_canada_junho_2023(self):
        self._extreme((-80, 48, -60, 56), 2023, 6, 5)               # Quebec

    def test_integridade(self):
        for p in sorted(glob.glob(os.path.join(D, 'grid', '*.parquet'))):
            g = pd.read_parquet(p, columns=['lat05', 'lon05', 'year', 'source', 'viirs_eq', 'lo', 'hi', 'level'])
            y = int(g.year.iloc[0])
            with self.subTest(year=y):
                self.assertEqual(set(g.source), {'AQUA' if y <= 2011 else 'SNPP' if y <= 2025 else 'N20'})
                self.assertFalse(g[['viirs_eq', 'lo', 'hi']].isna().any().any())
                self.assertTrue((g.lo <= g.viirs_eq).all() and (g.viirs_eq <= g.hi).all())
                self.assertTrue(g.lat05.between(-90, 90).all() and g.lon05.between(-180, 180).all())
                self.assertTrue(g.level.notna().all())


if __name__ == '__main__':
    unittest.main()
