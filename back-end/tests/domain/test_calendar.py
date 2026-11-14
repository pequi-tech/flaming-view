"""Matriz ano × mês."""
import unittest
from app.domain.calendar import calendar


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


if __name__ == '__main__':
    unittest.main()
