"""Rotas do contrato 1.1: previsão, prioridades, célula, áreas, camadas e assistente."""
from tests.fixtures import ApiCase
from tests.model_fixtures import RV, ModelApiCase


class TestPrevisao(ModelApiCase):
    def test_forecast_do_municipio(self):
        r = self.client.get('/forecast', params={'area_id': RV}).json()
        h1 = r['horizons'][0]
        self.assertEqual(h1['classes'], {'baixo': 0, 'normal': 1, 'alto': 0, 'critico': 1})
        self.assertEqual(h1['cells'], 2)
        self.assertAlmostEqual(h1['predicted'], 32.0)
        self.assertEqual(h1['metrics']['auc'], 0.7)
        self.assertEqual([a['id'] for a in r['lineage']], ['BRA', 'BR52', RV])

    def test_priorities_granularidade(self):
        mun = self.client.get('/priorities', params={'area_id': RV}).json()
        self.assertEqual(mun['granularity'], 'cell')
        top = mun['items'][0]
        self.assertEqual(top['id'], str(self.ids[0]))
        self.assertIn('R1', [x['rule_id'] for x in top['recommendations']])
        st = self.client.get('/priorities', params={'area_id': 'BR52'}).json()
        self.assertEqual((st['granularity'], st['items'][0]['id'], st['items'][0]['name']), ('municipality', RV, 'Rio Verde - GO'))
        self.assertIn('R7', [x['rule_id'] for x in st['items'][0]['recommendations']])
        box = self.client.get('/priorities', params={'bbox': '-57,-20,-55,-18'}).json()
        self.assertEqual(box['granularity'], 'hexagon')

    def test_celula(self):
        r = self.client.get(f'/cell/{self.ids[1]}').json()
        self.assertEqual(r['place']['ti_name'], 'TI Teste')
        self.assertEqual(r['place']['municipality_name'], 'Rio Verde - GO')
        self.assertEqual(len(r['history']), 24)
        self.assertEqual([f['level'] for f in r['forecast']], ['normal', 'normal', 'critico'])
        self.assertGreaterEqual(r['exposure']['e'], 0.8)
        self.assertEqual({x['rule_id'] for x in r['recommendations']}, {'R3', 'R5'})
        self.assertEqual(self.client.get('/cell/1').status_code, 404)

    def test_camadas(self):
        sq = self.client.get('/cells', params={'layer': 'forecast', 'horizon': 1, 'area_id': RV}).json()
        hx = self.client.get('/cells', params={'layer': 'forecast', 'horizon': 1, 'area_id': RV, 'shape': 'h3', 'h3_res': 5}).json()
        self.assertAlmostEqual(sum(c['value'] for c in sq['cells']), sum(c['value'] for c in hx['cells']), places=3)
        ipp = self.client.get('/cells', params={'layer': 'ipp', 'area_id': RV, 'shape': 'h3', 'h3_res': 6}).json()
        self.assertEqual(len(ipp['cells']), 2)
        self.assertIn(ipp['cells'][0]['level'], ('baixo', 'medio', 'alto', 'critico'))
        self.assertEqual(self.client.get('/cells', params={'layer': 'history'}).status_code, 422)

    def test_areas(self):
        r = self.client.get('/areas', params={'q': 'rio ver'}).json()
        self.assertEqual(r['areas'][0]['area_id'], RV)
        self.assertEqual(self.client.get(f'/areas/{RV}/geometry').json()['type'], 'Polygon')
        self.assertEqual(self.client.get('/areas/XX/geometry').status_code, 404)

    def test_method_expoe_ipp_e_modelo(self):
        m = self.client.get('/method').json()
        self.assertEqual(m['ipp']['weights'], {'n': 0.5, 'v': 0.25, 'e': 0.25})
        self.assertEqual(m['model']['model_version'], 'rf-test')
        self.assertEqual(len(m['rules']), 8)

    def test_assistente_em_sse_com_contexto(self):
        r = self.client.post('/assistant', json={'messages': [{'role': 'user', 'content': 'Por quê?'}],
                                                 'area_id': RV, 'cell_id': self.ids[0], 'lang': 'en'})
        self.assertEqual(r.headers['content-type'].split(';')[0], 'text/event-stream')
        self.assertIn('"text": "Olá "', r.text)
        self.assertTrue(r.text.rstrip().endswith('[DONE]'))
        system = self.llm.calls[0][0]
        self.assertIn('English', system)
        self.assertIn('"/cell"', system)


class TestSemModelo(ApiCase):
    def test_release_10_responde_503(self):
        r = self.client.get('/forecast', params={'area_id': RV})
        self.assertEqual((r.status_code, r.json()['error']['code']), (503, 'model_unavailable'))

    def test_assistente_sem_chave(self):
        client = self.make_client()
        r = client.post('/assistant', json={'messages': [{'role': 'user', 'content': 'oi'}]})
        self.assertEqual((r.status_code, r.json()['error']['code']), (503, 'assistant_unavailable'))
        self.assertNotIn('sk-', r.text)


class TestMotivoDoAssistente(ModelApiCase):
    def test_sem_credito_vira_motivo_billing_sem_vazar_mensagem(self):
        from app.domain.errors import AssistantUnavailable

        def falha(system, messages):
            raise AssistantUnavailable('billing')
            yield  # noqa: gerador

        self.llm.stream = falha
        r = self.client.post('/assistant', json={'messages': [{'role': 'user', 'content': 'oi'}], 'area_id': RV})
        self.assertIn('"reason": "billing"', r.text)
        self.assertTrue(r.text.rstrip().endswith('[DONE]'))


class TestOrdemDoPlano(ModelApiCase):
    def test_padrao_e_acao_mais_grave_e_ipp_continua_disponivel(self):
        acao = self.client.get('/priorities', params={'area_id': RV}).json()
        self.assertEqual(acao['sort'], 'action')
        self.assertEqual(acao['total'], 2)
        self.assertEqual(acao['items'][0]['id'], str(self.ids[0]))          # R1 vem antes de R3/R5
        ipp = self.client.get('/priorities', params={'area_id': RV, 'sort': 'ipp', 'limit': 1}).json()
        self.assertEqual((ipp['sort'], len(ipp['items']), ipp['total']), ('ipp', 1, 2))
        self.assertEqual(self.client.get('/priorities', params={'area_id': RV, 'sort': 'x'}).status_code, 422)


class TestNasaPower(ModelApiCase):
    def test_fatores_e_regra_r4(self):
        seca = self.client.get(f'/cell/{self.ids[0]}').json()
        rain = next(d for d in seca['drivers'] if d['key'] == 'rain')
        self.assertEqual((rain['available'], rain['value'], rain['months']), (True, -0.4, '2014-05..2014-07'))
        self.assertIn('R4', [r['rule_id'] for r in seca['recommendations']])
        sem = self.client.get(f'/cell/{self.ids[1]}').json()
        self.assertFalse(next(d for d in sem['drivers'] if d['key'] == 'rain')['available'])
        mun = self.client.get('/priorities', params={'area_id': 'BR52'}).json()['items'][0]
        self.assertIn('R4', [r['rule_id'] for r in mun['recommendations']])
