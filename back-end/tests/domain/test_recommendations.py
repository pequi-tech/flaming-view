"""Uma regra por teste (RF-API-05), mais a célula sem recomendação."""
import unittest

from app.domain.recommendations import cell_context, recommend

ids = lambda ctx: [r['rule_id'] for r in recommend(ctx)]


class TestRegras(unittest.TestCase):
    def base(self, k=(1, 1, 1), e=0.1, e_ti=0.0, v=0.1, **kw):
        return {**cell_context(list(k), e, e_ti, v), **kw}

    def test_sem_recomendacao(self):
        self.assertEqual(ids(self.base()), [])

    def test_r1_critico_m1(self):
        self.assertIn('R1', ids(self.base(k=(3, 3, 3))))

    def test_r2_alto_e_exposto(self):
        self.assertIn('R2', ids(self.base(k=(2, 2, 2), e=0.8)))
        self.assertNotIn('R2', ids(self.base(k=(2, 2, 2), e=0.5)))

    def test_r3_ti_critica_em_algum_horizonte(self):
        self.assertIn('R3', ids(self.base(k=(1, 1, 3), e_ti=1.0)))

    def test_r4_seca(self):
        self.assertIn('R4', ids(self.base(rain_anomaly=-0.35)))
        self.assertNotIn('R4', ids(self.base(rain_anomaly=-0.1)))

    def test_r5_pico_depois(self):
        self.assertIn('R5', ids(self.base(k=(1, 2, 2))))

    def test_r6_recorrente_normal(self):
        self.assertIn('R6', ids(self.base(v=0.8)))

    def test_r7_municipio_com_20pct_critico(self):
        self.assertIn('R7', ids(self.base(crit_share=0.25)))
        self.assertNotIn('R7', ids(self.base(crit_share=0.1)))

    def test_r8_mes_corrente_critico(self):
        self.assertIn('R8', ids(self.base(current_level='critico')))

    def test_ordem_por_severidade_e_id(self):
        out = ids(self.base(k=(3, 3, 3), e=0.9, e_ti=1.0, crit_share=0.5))
        self.assertEqual(out, ['R1', 'R7', 'R2', 'R3'])

    def test_toda_regra_vira_decisao(self):
        r = recommend(self.base(k=(3, 3, 3)))[0]
        self.assertEqual((r['decisions'], r['severity'], r['key']), (['D1', 'D5'], 'high', 'rec.R1'))


class TestGravidade(unittest.TestCase):
    def test_r8_r7_r1_depois_r2_r4_depois_r5_r6(self):
        from app.domain.recommendations import action_rank
        rank = lambda *ids: action_rank([{'rule_id': r} for r in ids])
        self.assertLess(rank('R8'), rank('R7'))
        self.assertLess(rank('R7'), rank('R1', 'R6'))
        self.assertLess(rank('R1'), rank('R3'))
        self.assertLess(rank('R4'), rank('R5'))
        self.assertLess(rank('R6'), rank())
