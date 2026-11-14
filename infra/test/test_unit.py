"""Regras do pipeline em dados sintéticos: cada teste quebra se a regra correspondente for violada."""
import os, sys, unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import aggregate as ag
import harmonize as hz


def det(lat, lon, date, sat='N', conf='n', dn='D', typ=0):
    return dict(latitude=lat, longitude=lon, acq_date=date, satellite=sat, confidence=conf, daynight=dn, type=typ)


class TestClean(unittest.TestCase):
    def test_filtros_e_sensor(self):
        d = pd.DataFrame([
            det(-10, -50, '2020-08-01', 'Aqua', 85),           # fica
            det(-10, -50, '2020-08-01', 'Aqua', 29),           # MODIS baixa confiança -> sai
            det(-10, -50, '2020-08-01', 'N', 'l'),             # VIIRS low -> sai
            det(-10, -50, '2020-08-01', 'N20', 'nominal'),     # formato da API NRT -> fica
            det(-10, -50, '2020-08-01', 'N', 'h', typ=2),      # fonte estática -> sai
            det(-10, -50, '2020-08-01', 'Terra', 50),          # fica, src TERRA
        ])
        self.assertEqual(sorted(ag.clean(d).src), ['AQUA', 'N20', 'TERRA'])

    def test_sensor_desconhecido_cai(self):
        self.assertEqual(len(ag.clean(pd.DataFrame([det(-10, -50, '2020-08-01', 'X', 'h')]))), 0)


class TestCellDays(unittest.TestCase):
    def test_raw_vs_cd01(self):
        d = ag.clean(pd.DataFrame([
            det(-10.001, -50.001, '2020-08-01'),   # mesma célula 0,01° e mesmo dia -> 1 célula-dia
            det(-10.002, -50.002, '2020-08-01'),
            det(-10.001, -50.001, '2020-08-02'),   # outro dia -> +1
            det(-10.001, -50.001, '2020-08-01', dn='N'),  # noite conta separado
        ]))
        g = ag.cell_days(d).set_index('daynight')
        self.assertEqual(int(g.loc['D', 'raw']), 3)
        self.assertEqual(int(g.loc['D', 'cd01']), 2)
        self.assertEqual(int(g.loc['N', 'cd01']), 1)
        self.assertTrue((g.lat05 == -10.05).all() and (g.lon05 == -50.05).all())  # célula 0,05° correta p/ negativos

    def test_qualquer_lugar_do_mundo(self):
        d = ag.clean(pd.DataFrame([det(64.123, -150.456, '2020-07-01'), det(-33.9, 151.2, '2020-01-01'),
                                   det(0.001, 179.999, '2020-01-01'), det(0.35, 10.35, '2020-01-01')]))
        g = ag.cell_days(d)
        self.assertEqual(len(g), 4)
        self.assertEqual(sorted(g.lat05), [-33.9, 0.0, 0.35, 64.1])     # bordas exatas: -33.9 e 0.35 abrem célula
        self.assertEqual(sorted(g.lon05), [-150.5, 10.35, 151.2, 179.95])


B = lambda m: 400 + 40 * m                       # SNPP por mês: variação sazonal, para R² fazer sentido


def synth(cells, years=range(2013, 2022)):
    """cells = {(lat, lon): (k, escala_snpp)}  ->  AQUA = SNPP * k (relação exata)."""
    rows = []
    for (la, lo), (k, sc) in cells.items():
        for y in years:
            for m in range(1, 13):
                b = B(m) * sc
                rows.append(dict(src='SNPP', daynight='D', year=y, month=m, lat05=float(la), lon05=float(lo), raw=b, cd01=b))
                rows.append(dict(src='AQUA', daynight='D', year=y, month=m, lat05=float(la), lon05=float(lo), raw=b * k, cd01=b * k))
    return pd.DataFrame(rows)


class TestFactors(unittest.TestCase):
    def test_hierarquia_de_fallback(self):
        cells = {
            (-10.0, -50.0): (0.25, 1),       # rica: fator próprio (c2)
            (-14.0, -56.0): (0.50, 1),       # rica, bloco 10° (-20,-60)
            (-12.0, -54.0): (0.50, 0.001),   # esparsa no mesmo bloco 10° -> c10
            (-16.0, 20.0): (0.50, 0.001),    # esparsa, bloco 10° sozinho, mesma faixa -20 -> band
            (62.0, 100.0): (0.50, 0.001),    # esparsa, faixa 60 sozinha -> global
        }
        fit = hz.fit_factor(hz.to_c2(synth(cells)), 'AQUA', 'SNPP', hz.CAL)
        q = pd.DataFrame({'lat05': [la for la, _ in cells], 'lon05': [lo for _, lo in cells], 'month': 8})
        f, lvl = hz.lookup(fit, q)
        self.assertEqual(list(lvl), ['c2', 'c2', 'c10', 'band', 'global'])
        self.assertAlmostEqual(f[0], 0.25)
        self.assertAlmostEqual(f[1], 0.50)
        self.assertAlmostEqual(f[2], 0.50, places=3)                 # herda do bloco rico vizinho

    def test_celula_nunca_vista_usa_hierarquia(self):
        fit = hz.fit_factor(hz.to_c2(synth({(-10.0, -50.0): (0.25, 1)})), 'AQUA', 'SNPP', hz.CAL)
        f, lvl = hz.lookup(fit, pd.DataFrame({'lat05': [-5.0, 45.0], 'lon05': [-45.0, 10.0], 'month': [8, 8]}))
        self.assertEqual(list(lvl), ['c10', 'global'])
        self.assertTrue(np.allclose(f, 0.25))

    def test_holdout_perfeito(self):
        a = synth({(-10.0, -50.0): (0.25, 1), (40.0, -120.0): (0.4, 1)})
        t = hz.to_c2(a)
        m = hz.holdout_metrics(t, hz.fit_factor(t, 'AQUA', 'SNPP', hz.CAL))
        self.assertEqual(m['mape_total_monthly_pct'], 0.0)
        self.assertEqual(m['r2_cell2_month'], 1.0)
        self.assertEqual(m['level_share'], {'c2': 1.0})

    def test_grid_por_fonte(self):
        a = synth({(-10.0, -50.0): (0.25, 1)})
        fit = hz.fit_factor(hz.to_c2(a), 'AQUA', 'SNPP', hz.CAL)
        aq = hz.grid_part(a[(a.src == 'AQUA') & (a.year == 2020)], 'AQUA', fit, fit, 0.9, 1.1)
        sn = hz.grid_part(a[(a.src == 'SNPP') & (a.year == 2020)], 'SNPP', fit, fit, 0.9, 1.1)
        aug = lambda g: g[g.month == 8].iloc[0]
        self.assertAlmostEqual(aug(aq).viirs_eq, B(8))               # AQUA convertido = o que o SNPP viu
        self.assertEqual(aug(sn).viirs_eq, B(8))
        self.assertTrue(aug(aq).lo < B(8) < aug(aq).hi)
        self.assertTrue(aug(sn).lo == aug(sn).hi == B(8) and aug(sn).level == 'observed')
        self.assertFalse(aq.viirs_eq.isna().any() or np.isinf(aq.viirs_eq).any())


if __name__ == '__main__':
    unittest.main()
