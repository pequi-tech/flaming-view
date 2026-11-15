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


class TestTravaDeHonestidade(unittest.TestCase):
    cuts = {'medio': 0.4, 'alto': 0.6, 'critico': 0.75}

    def test_maxima_so_com_fogo_acima_do_normal(self):
        self.assertEqual(ipp_level(0.9, self.cuts, fire_k=1), 'alto')        # fogo normal: no máximo Alta
        self.assertEqual(ipp_level(0.9, self.cuts, fire_k=2), 'critico')
        self.assertEqual(ipp_level(0.9, self.cuts, fire_k=3), 'critico')
        self.assertEqual(ipp_level(0.5, self.cuts, fire_k=0), 'medio')        # abaixo de Máxima não muda
