"""/calendar e /series."""
import unittest
from tests.fixtures import ApiCase, PANTANAL, CHUKOTKA


class TestCalendarRoutes(ApiCase):
    def test_calendario(self):
            r = self.client.get('/calendar', params={'bbox': PANTANAL})
            self.assertEqual(r.status_code, 200)
            m = r.json()['months']
            self.assertEqual(len(m), 4 * 12)                                       # matriz completa
            aug = [x for x in m if x['month'] == 8]
            self.assertEqual([x['value'] for x in aug], [10, 20, 30, 40])
            self.assertEqual(aug[-1]['level'], 'critico')
            self.assertEqual(aug[0]['source'], 'AQUA')
            self.assertTrue(aug[0]['estimated'] and aug[0]['lo'] < 10 < aug[0]['hi'])
            self.assertEqual([x['value'] for x in m if x['month'] == 3], [0, 0, 0, 0])   # mês sem linha = zero
            self.assertIn('max-age', r.headers['cache-control'])

    def test_calendario_nao_vaza_celula_fora_da_caixa(self):
            m = self.client.get('/calendar', params={'bbox': '-58,-22,-56.05,-16'}).json()['months']
            self.assertEqual(sum(x['value'] for x in m), 0)

    def test_antimeridiano(self):
            m = self.client.get('/calendar', params={'bbox': CHUKOTKA}).json()['months']
            self.assertEqual({x['value'] for x in m if x['month'] == 7}, {12.0})

    def test_recorte_de_anos(self):
            m = self.client.get('/calendar', params={'bbox': PANTANAL, 'from_year': 2012, 'to_year': 2013}).json()['months']
            self.assertEqual(sorted({x['year'] for x in m}), [2012, 2013])
            self.assertEqual(m[7]['median'], 25.0)

    def test_csv(self):
            r = self.client.get('/calendar', params={'bbox': PANTANAL, 'format': 'csv'})
            self.assertTrue(r.headers['content-type'].startswith('text/csv'))
            lines = r.text.strip().splitlines()
            self.assertEqual(lines[0].split(',')[:4], ['year', 'month', 'value', 'lo'])
            self.assertEqual(len(lines), 49)

    def test_serie(self):
            y = self.client.get('/series', params={'bbox': PANTANAL}).json()['years']
            self.assertEqual([(r['year'], r['value']) for r in y], [(2010, 11), (2011, 21), (2012, 31), (2013, 41)])
    def test_validacao(self):
        for params in [{'bbox': '1,2,3'}, {'bbox': PANTANAL, 'from_year': 1990},
                       {'bbox': PANTANAL, 'from_year': 2013, 'to_year': 2012}, {}]:
            with self.subTest(params=params):
                self.assertEqual(self.client.get('/calendar', params=params).status_code, 422)


if __name__ == '__main__':
    unittest.main()
