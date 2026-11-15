"""/current: FIRMS tempo real, cache SQLite e falhas."""
import unittest
from tests.fixtures import ApiCase, PANTANAL, CHUKOTKA, nrt_row


class TestRealtimeRoutes(ApiCase):
    def setUp(self):
            super().setUp()
            self.firms.rows = (nrt_row(-19.001, -56.001, '2014-08-02') + nrt_row(-19.002, -56.002, '2014-08-02')   # mesma célula-dia
                               + nrt_row(-19.001, -56.001, '2014-08-05') + nrt_row(-19.0, -56.0, '2014-08-06', conf='l'))

    def test_mes_corrente(self):
            r = self.client.get('/current', params={'bbox': PANTANAL}).json()
            self.assertEqual((r['year'], r['month'], r['day']), (2014, 8, 10))
            self.assertEqual(r['value_to_date'], 2)                               # 2 células-dia válidas
            self.assertAlmostEqual(r['projected'], 2 * 31 / 10, places=2)
            self.assertEqual(r['median'], 25.0)
            self.assertEqual(r['level'], 'baixo')
            self.assertFalse(r['stale'])
            self.assertEqual(len(self.firms.calls), 2)                            # dias 1-5 e 6-10
            self.assertTrue(all('TESTKEY' in u and 'VIIRS_NOAA21_NRT' in u for u in self.firms.calls))

    def test_cache_sqlite(self):
            self.client.get('/current', params={'bbox': PANTANAL})
            self.client.get('/current', params={'bbox': PANTANAL})
            self.assertEqual(len(self.firms.calls), 2)                            # segunda vez veio do cache
            other = self.make_client()                                            # outro processo, mesmo arquivo
            other.get('/current', params={'bbox': PANTANAL})
            self.assertEqual(len(self.firms.calls), 2)

    def test_janelas_fechadas_ficam_no_cache(self):
            """Dias 1-5 já não mudam no NRT: mesmo com TTL zero, só a janela recente (6-10) volta ao FIRMS."""
            self.client.get('/current', params={'bbox': PANTANAL})
            self.make_client(cache_ttl=0).get('/current', params={'bbox': PANTANAL})
            self.assertEqual(len(self.firms.calls), 3)
            self.assertTrue(self.firms.calls[-1].endswith('/5/2014-08-06'))

    def test_firms_fora_do_ar_usa_ultimo_snapshot(self):
            self.client.get('/current', params={'bbox': PANTANAL})
            self.firms.fail = True
            stale = self.make_client(cache_ttl=0).get('/current', params={'bbox': PANTANAL})
            self.assertEqual(stale.status_code, 200)
            self.assertTrue(stale.json()['stale'])
            self.assertEqual(stale.json()['value_to_date'], 2)

    def test_firms_fora_do_ar_sem_cache(self):
            self.firms.fail = True
            r = self.client.get('/current', params={'bbox': PANTANAL})
            self.assertEqual(r.status_code, 503)
            self.assertEqual(r.json()['error']['code'], 'realtime_unavailable')

    def test_sem_chave(self):
            self.assertEqual(self.make_client(map_key=None).get('/current', params={'bbox': PANTANAL}).status_code, 503)

    def test_antimeridiano_vira_duas_consultas(self):
            self.client.get('/current', params={'bbox': CHUKOTKA})
            areas = {u.split('/')[-3] for u in self.firms.calls}
            self.assertEqual(areas, {'170,60,180,70', '-180,60,-170,70'})


if __name__ == '__main__':
    unittest.main()
