"""Regras de negócio puras, sem IO."""
import unittest
from app.domain import BBox, InvalidArea, calendar, climatology, assess, project


class TestBBox(unittest.TestCase):
    def test_parse(self):
        b = BBox.parse('-58,-22,-54,-16')
        self.assertEqual((b.w, b.s, b.e, b.n), (-58, -22, -54, -16))
        self.assertFalse(b.crosses_antimeridian)

    def test_invalidas(self):
        for t in ['', '1,2,3', 'a,b,c,d', '-58,-16,-54,-22', '-200,0,10,10', '0,-91,10,10', '10,0,10,5']:
            with self.subTest(t=t), self.assertRaises(InvalidArea):
                BBox.parse(t)

    def test_antimeridiano(self):
        b = BBox.parse('170,50,-170,70')                    # Rússia oriental / Alasca
        self.assertTrue(b.crosses_antimeridian)
        self.assertEqual(b.lon_ranges(), [(170, 180), (-180, -170)])

    def test_celulas_que_tocam_a_caixa(self):
        """Célula de 0,05° com canto SW em lat entra se [lat, lat+0,05) intersecta [s, n]."""
        lo, hi = BBox.parse('0,-10,1,-5').lat_open_interval()
        self.assertAlmostEqual(lo, -10.05)                  # lat > -10,05: a célula -10,05 ([−10,05, −10,00)) fica fora
        self.assertEqual(hi, -5)                            # lat < -5: a célula -5,00 começa na borda norte, fica fora


def series(years, month_values):
    """{(ano, mês): valor} com o mesmo perfil mensal em todos os anos."""
    return {(y, m): v for y in years for m, v in month_values.items()}


class TestClimatologia(unittest.TestCase):
    def test_ano_sem_linha_conta_como_zero(self):
        v = {(2003, 8): 10.0, (2004, 8): 20.0}               # 2005 sem focos em agosto
        c = climatology(v, range(2003, 2006))[8]
        self.assertEqual(c['median'], 10.0)                 # mediana de [10, 20, 0]

    def test_percentis(self):
        v = {(y, 8): float(y - 2000) for y in range(2001, 2011)}   # 1..10
        c = climatology(v, range(2001, 2011))[8]
        self.assertAlmostEqual(c['median'], 5.5)
        self.assertAlmostEqual(c['p90'], 9.1)


class TestNivel(unittest.TestCase):
    clim = {'p25': 5.0, 'median': 10.0, 'p75': 20.0, 'p90': 40.0}

    def test_niveis(self):
        for v, lvl in [(2, 'baixo'), (10, 'normal'), (25, 'alto'), (40, 'critico'), (500, 'critico')]:
            with self.subTest(v=v):
                self.assertEqual(assess(v, self.clim)['level'], lvl)

    def test_razao(self):
        self.assertEqual(assess(25, self.clim)['ratio'], 2.5)
        self.assertIsNone(assess(3, {'p25': 0, 'median': 0, 'p75': 0, 'p90': 0})['ratio'])   # mediana zero: sem razão

    def test_lugar_sem_fogo_nunca_e_alerta(self):
        self.assertEqual(assess(0, {'p25': 0, 'median': 0, 'p75': 0, 'p90': 0})['level'], 'normal')


class TestCalendario(unittest.TestCase):
    def test_matriz_completa_com_zeros(self):
        v = {(2010, 1): 4.0, (2011, 9): 100.0}
        cal = calendar(v, {}, {}, {}, range(2010, 2012), range(2010, 2012))
        self.assertEqual(len(cal), 24)
        self.assertEqual([c['value'] for c in cal if c['year'] == 2010 and c['month'] == 9], [0.0])
        sep11 = next(c for c in cal if (c['year'], c['month']) == (2011, 9))
        self.assertEqual(sep11['median'], 50.0)
        self.assertEqual(sep11['ratio'], 2.0)

    def test_incerteza_e_fonte(self):
        cal = calendar({(2005, 8): 10.0}, {(2005, 8): 8.0}, {(2005, 8): 13.0}, {2005: 'AQUA'}, range(2005, 2006), range(2005, 2006))
        aug = cal[7]
        self.assertEqual((aug['lo'], aug['hi'], aug['source'], aug['estimated']), (8.0, 13.0, 'AQUA', True))


class TestProjecao(unittest.TestCase):
    def test_mes_corrente(self):
        self.assertEqual(project(100, day=10, days_in_month=30), 300)
        self.assertEqual(project(100, day=30, days_in_month=30), 100)


if __name__ == '__main__':
    unittest.main()
