import unittest

from app.domain.ipp import explain, ipp, ipp_level


class TestIpp(unittest.TestCase):
    def test_formula(self):
        self.assertAlmostEqual(ipp(0.64, 0.81, 0.16), 0.64 ** 0.5 * 0.81 ** 0.25 * 0.16 ** 0.25)

    def test_piso_nao_zera(self):
        self.assertAlmostEqual(ipp(1, 1, 0), 0.05 ** 0.25)
        self.assertGreater(ipp(0, 0, 0), 0)

    def test_classes(self):
        cuts = {'medio': 0.4, 'alto': 0.6, 'critico': 0.75}
        self.assertEqual([ipp_level(x, cuts) for x in (0.1, 0.4, 0.7, 0.9)], ['baixo', 'medio', 'alto', 'critico'])

    def test_explicacao(self):
        self.assertEqual(explain(0.9, 0.2, 0.7), {'dominant': ['n', 'e'], 'weak': 'v'})
