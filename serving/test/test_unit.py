"""Cada teste quebra UMA regra do contrato e exige que o validador recuse."""
import json, os, sys, tempfile, unittest
import pandas as pd
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import publish as pb


def infra_grid(year=2020, n=12, **over):
    """Saída válida do infra (colunas antigas): uma célula, n meses."""
    src = pb.source_for(year)
    obs = src == 'SNPP'
    k = 1.0 if obs else 0.25
    d = pd.DataFrame({'lat05': -10.05, 'lon05': -50.05, 'year': year, 'month': range(1, n + 1), 'source': src,
                      'raw': 10, 'cd01': 8 * k, 'factor': k, 'level': 'observed' if obs else 'c2'})
    d['viirs_eq'] = d.cd01 / d.factor
    d['lo'] = d.viirs_eq if obs else d.viirs_eq / 1.3
    d['hi'] = d.viirs_eq if obs else d.viirs_eq / 0.7
    for c, v in over.items():
        d[c] = v
    return d


def errors(raw, year=2020):
    g, _ = pb.standardize_grid(raw)
    return pb.check_grid(g, year)


class TestGridOk(unittest.TestCase):
    def test_validos_passam(self):
        for y in (2005, 2020, 2026):
            with self.subTest(year=y):
                self.assertEqual(errors(infra_grid(y), y), [])

    def test_padronizacao(self):
        g, rep = pb.standardize_grid(pd.concat([infra_grid(), infra_grid(lat05=-75.0)]))
        self.assertEqual(list(g.columns), list(pb.GRID['columns']))
        self.assertEqual(rep['dropped_antarctica_rows'], 12)
        self.assertEqual(str(g.year.dtype), 'int16')
        self.assertEqual(int(g.cell_id.iloc[0]), (-201 + 1800) * 7200 + (-1001 + 3600))

    def test_cell_id_cobre_o_globo(self):
        self.assertEqual(int(pb.cell_id(pd.Series([-90.0]), pd.Series([-180.0]))[0]), 0)
        self.assertEqual(int(pb.cell_id(pd.Series([89.95]), pd.Series([179.95]))[0]), 3600 * 7200 - 1)


class TestGridRejeita(unittest.TestCase):
    def assertRejects(self, raw, fragment, year=2020):
        e = errors(raw, year)
        self.assertTrue(any(fragment in x for x in e), f'esperava "{fragment}" em {e}')

    def assertRaisesContract(self, raw, fragment):
        with self.assertRaises(pb.ContractError) as c:
            pb.standardize_grid(raw)
        self.assertIn(fragment, str(c.exception))

    def test_nulo(self):
        self.assertRaisesContract(infra_grid(cd01=[None] + [8] * 11), 'cell_days: 1 nulos')

    def test_fora_da_grade(self):
        self.assertRejects(infra_grid(lat05=-10.07), 'grade de 0,05')

    def test_lat_fora_do_intervalo(self):
        self.assertRejects(infra_grid(lon05=181.0), 'lon: acima do máximo')

    def test_source_errado_para_o_ano(self):
        self.assertRejects(infra_grid(source='AQUA'), 'source')

    def test_source_fora_do_enum(self):
        self.assertRaisesContract(infra_grid(source='TERRA'), "source: fora do enum ['TERRA']")

    def test_celulas_dia_maior_que_deteccoes(self):
        self.assertRejects(infra_grid(raw=5), 'cell_days > detections')

    def test_activity_inconsistente(self):
        self.assertRejects(infra_grid(viirs_eq=99.0, lo=99.0, hi=99.0), 'activity != cell_days')

    def test_fator_zero(self):
        self.assertRejects(infra_grid(2005, factor=0.0), 'factor: abaixo do mínimo')

    def test_snpp_convertido(self):
        self.assertRejects(infra_grid(level='c2'), 'observed')

    def test_faixa_invertida(self):
        self.assertRejects(infra_grid(2005, lo=1000.0), 'incerteza invertida')

    def test_duplicado(self):
        self.assertRejects(pd.concat([infra_grid(), infra_grid()]), 'duplicada')

    def test_ano_incompleto(self):
        self.assertRejects(infra_grid(n=11), 'ano completo com 11 meses')

    def test_ano_da_particao(self):
        self.assertRejects(infra_grid(2021), 'partição 2020')

    def test_coluna_faltando(self):
        self.assertRaisesContract(infra_grid().drop(columns='hi'), "faltando ['activity_hi']")


class TestPortoes(unittest.TestCase):
    def test_metricas_ruins(self):
        e = pb.check_metrics({'mape_total_monthly_pct': 12, 'r2_cell2_month': 0.8, 'level_share': {'c2': 0.5}})
        self.assertEqual(len(e), 3)

    def test_degrau_na_serie(self):
        self.assertEqual(pb.check_series({2010: 100, 2011: 110, 2012: 420}), ['atividade 2011->2012 mudou 3.8x'])
        self.assertEqual(pb.check_series({2010: 100, 2011: 120}), [])


class TestPublicacao(unittest.TestCase):
    def _infra(self, d, grids, metrics=None):
        os.makedirs(os.path.join(d, 'grid'))
        for y, g in grids.items():
            g.to_parquet(os.path.join(d, 'grid', f'{y}.parquet'))
        Path(os.path.join(d, 'metrics.json')).write_text(json.dumps(
            metrics or {'mape_total_monthly_pct': 4.7, 'r2_cell2_month': 0.96, 'level_share': {'c2': 0.98}}))
        pd.DataFrame({'link': ['AQUA_SNPP'], 'level': ['global'], 'lat': [None], 'lon': [None], 'month': [8], 'factor': [0.23]}
                     ).to_csv(os.path.join(d, 'factors.csv'), index=False)

    def test_publica_e_verifica(self):
        with tempfile.TemporaryDirectory() as t:
            self._infra(os.path.join(t, 'infra'), {2011: infra_grid(2011), 2012: infra_grid(2012)})
            path, man = pb.publish(os.path.join(t, 'infra'), os.path.join(t, 'rel'), 'v1')
            self.assertEqual(Path(os.path.join(t, 'rel', 'CURRENT')).read_text().strip(), 'v1')
            self.assertEqual(pb.verify(path), [])
            self.assertEqual(man['rows'], 24)
            with open(os.path.join(path, 'grid', 'year=2012.parquet'), 'ab') as fh: fh.write(b'x')     # corrompe
            self.assertEqual(pb.verify(path), ['grid/year=2012.parquet: checksum'])

    def test_rejeitada_nao_troca_a_atual(self):
        with tempfile.TemporaryDirectory() as t:
            self._infra(os.path.join(t, 'ok'), {2012: infra_grid(2012)})
            pb.publish(os.path.join(t, 'ok'), os.path.join(t, 'rel'), 'v1')
            self._infra(os.path.join(t, 'bad'), {2012: infra_grid(2012, raw=1)})
            with self.assertRaises(pb.ContractError):
                pb.publish(os.path.join(t, 'bad'), os.path.join(t, 'rel'), 'v2')
            self.assertEqual(Path(os.path.join(t, 'rel', 'CURRENT')).read_text().strip(), 'v1')
            self.assertEqual(sorted(os.listdir(os.path.join(t, 'rel'))), ['CURRENT', 'v1'])   # sem lixo da v2


if __name__ == '__main__':
    unittest.main()
