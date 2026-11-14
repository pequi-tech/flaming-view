"""Climatologia do mês e nível."""
import unittest
from app.domain.climatology import assess, climatology


class TestClimatologia(unittest.TestCase):
    def test_ano_sem_linha_conta_como_zero(self):
            v = {(2003, 8): 10.0, (2004, 8): 20.0}               # 2005 sem focos em agosto
            c = climatology(v, range(2003, 2006))[8]
            self.assertEqual(c['median'], 10.0)

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
            self.assertIsNone(assess(3, {'p25': 0, 'median': 0, 'p75': 0, 'p90': 0})['ratio'])

    def test_lugar_sem_fogo_nunca_e_alerta(self):
            self.assertEqual(assess(0, {'p25': 0, 'median': 0, 'p75': 0, 'p90': 0})['level'], 'normal')


if __name__ == '__main__':
    unittest.main()
