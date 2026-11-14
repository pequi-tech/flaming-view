"""BBox: validação, antimeridiano e seleção de células."""
import unittest
from app.domain.area import BBox
from app.domain.errors import InvalidArea


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
            self.assertEqual(hi, -5)


if __name__ == '__main__':
    unittest.main()
