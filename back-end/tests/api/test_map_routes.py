"""/cells (camada do globo)."""
import unittest
from tests.fixtures import ApiCase, PANTANAL


class TestMapRoutes(ApiCase):
    def test_celulas_para_o_globo(self):
            r = self.client.get('/cells', params={'year': 2013, 'month': 8, 'res': 1}).json()
            self.assertEqual(sorted((c['lat'], c['lon'], c['value']) for c in r['cells']), [(-19, -56, 40), (10, 10, 100)])
            r = self.client.get('/cells', params={'year': 2013, 'month': 8, 'res': 1, 'bbox': PANTANAL}).json()
            self.assertEqual(len(r['cells']), 1)
    def test_validacao(self):
        for params in [{'year': 2013, 'month': 13}, {'year': 2013, 'month': 8, 'res': 3}, {'year': 1990, 'month': 8}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/cells', params=params).status_code, 422)


if __name__ == '__main__':
    unittest.main()
