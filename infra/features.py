"""Conjunto de treino da previsão (RD-02, RD-04): série harmonizada em célula grossa × mês e features no mês de emissão t.

Tudo vira matriz A[célula, t] (t = meses desde jan/2003, zeros preenchidos). Uma linha = (célula, emissão t, horizonte h),
alvo no mês T = t + h. Nenhuma feature lê A depois de t (teste em test/test_features.py). A climatologia do mês-alvo
usa só os anos de treino, então também não olha o período de teste.
"""
import numpy as np
import pandas as pd
import duckdb

Y0 = 2003
TRAIN_LAST = 2022
LEVELS = ('baixo', 'normal', 'alto', 'critico')
SEAS = ['DJF', 'JFM', 'FMA', 'MAM', 'AMJ', 'MJJ', 'JJA', 'JAS', 'ASO', 'SON', 'OND', 'NDJ']
FEATURES = ['a_t', 'a_t1', 'a_t2', 'a_T12', 'ma3', 'ma12', 'clim_med', 'clim_p75', 'clim_p90',
            'msin', 'mcos', 'lat', 'oni', 'oni3']


def oni_table(path):
    """ONI (NOAA CPC): a estação centrada no mês m vira o valor do mês m. -> year, month, oni."""
    d = pd.read_csv(path, sep=r'\s+')
    return pd.DataFrame({'year': d.YR, 'month': d.SEAS.map({s: i + 1 for i, s in enumerate(SEAS)}), 'oni': d.ANOM})


def coarse_matrix(grid_glob, res, last_year):
    """A[célula, t] da soma de activity em células de `res` graus, jan/2003..dez/last_year (+ meses parciais seguintes)."""
    rows = duckdb.sql(f"""
        SELECT floor(lat05 / {res}) * {res} AS lat, floor(lon05 / {res}) * {res} AS lon,
               (year - {Y0}) * 12 + month - 1 AS t, sum(viirs_eq) AS a
        FROM read_parquet('{grid_glob}') GROUP BY ALL""").df()
    cells = rows[['lat', 'lon']].drop_duplicates().sort_values(['lat', 'lon']).reset_index(drop=True)
    cells['i'] = np.arange(len(cells))
    rows = rows.merge(cells, on=['lat', 'lon'])
    A = np.zeros((len(cells), int(rows.t.max()) + 1), np.float32)
    A[rows.i.to_numpy(), rows.t.to_numpy()] = rows.a.to_numpy()
    return cells[['lat', 'lon']], A


def climatology(A, last_year=TRAIN_LAST):
    """Por célula × mês do ano: p25, mediana, p75, p90 e média sobre 2003..last_year (zeros incluídos)."""
    n = (last_year - Y0 + 1) * 12
    Y = A[:, :n].reshape(len(A), -1, 12)                  # célula × ano × mês
    q = np.percentile(Y, [25, 50, 75, 90], axis=1)        # 4 × célula × mês
    return {'p25': q[0], 'median': q[1], 'p75': q[2], 'p90': q[3], 'mean': Y.mean(1)}


def classify(value, clim, m):
    """Mesma regra do back-end (domain/climatology.assess): 0 baixo, 1 normal, 2 alto, 3 critico; p90 = 0 -> normal."""
    p25, p75, p90 = clim['p25'][:, m], clim['p75'][:, m], clim['p90'][:, m]
    k = np.ones(len(value), np.int8)
    k[value < p25] = 0
    k[value >= p75] = 2
    k[value >= p90] = 3
    k[p90 <= 0] = 1
    return k


def features_at(A, t, h, lat, clim, oni):
    """Features da emissão t para o alvo T = t + h. Só lê A[:, ..t] (e A[:, T-12], que é <= t para h <= 12)."""
    T = t + h
    m = T % 12
    l = lambda x: np.log1p(np.maximum(x, 0))
    return pd.DataFrame({
        'a_t': l(A[:, t]), 'a_t1': l(A[:, t - 1]), 'a_t2': l(A[:, t - 2]), 'a_T12': l(A[:, T - 12]),
        'ma3': l(A[:, t - 2:t + 1].mean(1)), 'ma12': l(A[:, t - 11:t + 1].mean(1)),
        'clim_med': l(clim['median'][:, m]), 'clim_p75': l(clim['p75'][:, m]), 'clim_p90': l(clim['p90'][:, m]),
        'msin': np.float32(np.sin(2 * np.pi * m / 12)), 'mcos': np.float32(np.cos(2 * np.pi * m / 12)),
        'lat': lat, 'oni': oni.get(t - 1, 0.0), 'oni3': np.mean([oni.get(t - k, 0.0) for k in (1, 2, 3)]),
    })


def dataset(A, lat, clim, oni, h, t_range):
    """Linhas (célula, t) com alvo conhecido em T = t + h. Só células com p90 > 0 no mês-alvo (senão a classe é 'normal' por regra)."""
    parts = []
    for t in t_range:
        T = t + h
        if t < 12 or T >= A.shape[1]:
            continue
        ok = clim['p90'][:, T % 12] > 0
        f = features_at(A, t, h, lat, clim, oni)[ok]
        f['y_class'] = classify(A[ok, T], {k: v[ok] for k, v in clim.items()}, T % 12)
        f['y_log'] = np.log1p(A[ok, T])
        f['T_year'] = Y0 + T // 12
        f['cell'] = np.flatnonzero(ok)
        parts.append(f)
    return pd.concat(parts, ignore_index=True)
