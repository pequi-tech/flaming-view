"""Previsão mensal por classe (RD-05, RD-06): Random Forest por horizonte, validação temporal e desagregação para 0,05°.

  python model.py data            # lê data/grid/*.parquet e data/ext/oni.ascii.txt; grava data/model/

Treino com alvos <= 2022, teste com alvos 2023-2025. Resolução 0,5°; cai para 1° se AUC(M+1) < 0,70.
Classe prevista: 'critico' para as 10 % de linhas com maior P(crítico) no treino (o mesmo corte do "top-10 %"),
'alto' para as 25 % com maior P(alto ou crítico), 'baixo' se P(baixo) >= 0,5, senão 'normal'.
Saídas: model/predictions.parquet, model/metrics.json, model/features.parquet (amostra de treino).
"""
import datetime as dt, glob, json, os, sys
import numpy as np
import pandas as pd
import duckdb
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import roc_auc_score

import features as F

SEED = 0
HORIZONS = (1, 2, 3)
TRAIN_ROWS = 400_000            # ponytail: amostra para caber em minutos; subir se a máquina aguentar
AUC_MIN = 0.70
PARTIAL_BBOX = (-74, -34, -34, 6)   # 2026 só existe para o Brasil (RD-01)
MEDIAN_FLOOR = 5.0              # razão prevista ÷ mediana: abaixo disso um foco isolado viraria "anomalia" enorme


def fit_horizon(A, lat, clim, oni, h, last_t):
    rows = F.dataset(A, lat, clim, oni, h, range(12, last_t - h + 1))
    train, test = rows[rows.T_year <= F.TRAIN_LAST], rows[rows.T_year > F.TRAIN_LAST]
    train = train.sample(min(len(train), TRAIN_ROWS), random_state=SEED)
    kw = dict(min_samples_leaf=20, max_features='sqrt', n_jobs=-1, random_state=SEED)
    clf = RandomForestClassifier(120, **kw).fit(train[F.FEATURES], train.y_class)
    reg = RandomForestRegressor(60, **kw).fit(train[F.FEATURES], train.y_log)
    p_tr = clf.predict_proba(train[F.FEATURES])
    cuts = {'crit': float(np.quantile(p_tr[:, 3], 0.90)), 'high': float(np.quantile(p_tr[:, 2:].sum(1), 0.75))}
    p = clf.predict_proba(test[F.FEATURES])[:, 3]
    crit = (test.y_class == 3).to_numpy()
    top = p >= np.quantile(p, 0.90)
    mae = float(np.abs(reg.predict(test[F.FEATURES]) - test.y_log).mean())
    mae_base = float(np.abs(test.clim_med - test.y_log).mean())        # baseline: a mediana do mês (log1p)
    metrics = {'auc': round(float(roc_auc_score(crit, p)), 3), 'top10_precision': round(float(crit[top].mean()), 3),
               'base_rate': round(float(crit.mean()), 3), 'mae': round(mae, 3), 'mae_baseline': round(mae_base, 3),
               'gain': round(1 - mae / mae_base, 3), 'n_train': len(train), 'n_test': len(test),
               'features': F.FEATURES, 'importances': [round(float(x), 4) for x in clf.feature_importances_]}
    return clf, reg, cuts, metrics, train


def to_class(p, cuts):
    k = np.ones(len(p), np.int8)
    k[p[:, 0] >= 0.5] = 0
    k[p[:, 2:].sum(1) >= cuts['high']] = 2
    k[p[:, 3] >= cuts['crit']] = 3
    return k


def forecast(A, cells, clim, clim_all, oni, h, t, clf, reg, cuts):
    """Previsão em célula grossa para emissão t: classe, contagem e faixa p10-p90 das árvores.
    Features com a climatologia do treino (igual ao ajuste); razão e regra p90 = 0 com a série inteira (igual ao back-end)."""
    X = F.features_at(A, t, h, cells.lat.to_numpy(np.float32), clim, oni)
    m = (t + h) % 12
    trees = np.stack([e.predict(X.to_numpy()) for e in reg.estimators_])
    k = np.ones(len(X), np.int8)
    ok = clim_all['p90'][:, m] > 0
    if ok.any():
        k[ok] = to_class(clf.predict_proba(X[ok]), cuts)
    pred = np.expm1(trees.mean(0)).clip(0)
    return pd.DataFrame({'class_k': k, 'predicted_c': pred, 'lo_c': np.expm1(np.quantile(trees, .1, 0)).clip(0),
                         'hi_c': np.expm1(np.quantile(trees, .9, 0)).clip(0),
                         'ratio': pred / np.maximum(clim_all['median'][:, m], MEDIAN_FLOOR)})


def fine_climatology(grid_glob, res, years):
    """Média do mês por célula 0,05° (todos os anos completos) e a célula grossa a que ela pertence."""
    return duckdb.sql(f"""
        SELECT (round(lat05 * 20) + 1800)::INT * 7200 + (round(lon05 * 20) + 3600)::INT AS cell_id,
               floor(lat05 / {res}) * {res} AS lat, floor(lon05 / {res}) * {res} AS lon, month,
               sum(viirs_eq) / {len(years)} AS mean_m
        FROM read_parquet('{grid_glob}') WHERE year BETWEEN {years[0]} AND {years[-1]} GROUP BY ALL""").df()


def main(data):
    grid = os.path.join(data, 'grid', '*.parquet')
    out = os.path.join(data, 'model')
    os.makedirs(out, exist_ok=True)
    oni_df = F.oni_table(os.path.join(data, 'ext', 'oni.ascii.txt'))
    oni = {(y - F.Y0) * 12 + m - 1: v for y, m, v in oni_df.itertuples(index=False)}
    years = sorted(int(os.path.basename(p)[:4]) for p in glob.glob(grid))
    full = [y for y in years if y <= 2025]
    for res in (0.5, 1.0):
        cells, A = F.coarse_matrix(grid, res, full[-1])
        clim = F.climatology(A)
        last_full_t = (full[-1] - F.Y0 + 1) * 12 - 1
        fits = {h: fit_horizon(A, cells.lat.to_numpy(np.float32), clim, oni, h, last_full_t) for h in HORIZONS}
        print(res, {h: f[3]['auc'] for h, f in fits.items()}, flush=True)
        if fits[1][3]['auc'] >= AUC_MIN:
            break
    # emissão: último mês com dado. Fora da cobertura parcial (Brasil em 2026) fica em dez/último ano completo.
    last_t = A.shape[1] - 1
    w, s, e, n = PARTIAL_BBOX
    in_partial = cells.lat.between(s, n) & cells.lon.between(w, e)
    has_partial = last_t > last_full_t
    clim_all = F.climatology(A, full[-1])                 # para a razão prevista e a desagregação: série inteira
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    version = f'rf-{res:g}deg-{F.Y0 + last_t // 12}{last_t % 12 + 1:02d}'
    fine = fine_climatology(grid, res, full)
    preds = []
    for h, (clf, reg, cuts, _, _) in fits.items():
        parts = []
        for t, mask in ((last_t, in_partial if has_partial else np.ones(len(cells), bool)),
                        (last_full_t, ~in_partial if has_partial else np.zeros(len(cells), bool))):
            if not mask.any():
                continue
            fc = forecast(A, cells, clim, clim_all, oni, h, t, clf, reg, cuts)[np.asarray(mask)]
            T = t + h
            fc = fc.assign(lat=cells.lat[np.asarray(mask)].to_numpy(), lon=cells.lon[np.asarray(mask)].to_numpy(),
                           forecast_month=f'{F.Y0 + T // 12}-{T % 12 + 1:02d}', month=T % 12 + 1,
                           recent_data=bool(has_partial and t == last_t))
            parts.append(fc)
        fc = pd.concat(parts)
        f = fine.merge(fc[['lat', 'lon', 'month']].drop_duplicates(), on=['lat', 'lon', 'month'], how='inner')
        f['share'] = f.mean_m / f.groupby(['lat', 'lon']).mean_m.transform('sum')
        # todas as células com histórico, mesmo sem fogo naquele mês (share 0)
        allc = fine[['cell_id', 'lat', 'lon']].drop_duplicates('cell_id')
        d = allc.merge(fc, on=['lat', 'lon']).merge(f[['cell_id', 'share']], on='cell_id', how='left')
        d['share'] = d.share.fillna(0.0)
        d = d.assign(horizon=np.int8(h), **{'class': np.array(F.LEVELS)[d.class_k]},
                     predicted=(d.predicted_c * d.share).astype('float32'), lo=(d.lo_c * d.share).astype('float32'),
                     hi=(d.hi_c * d.share).astype('float32'))
        d['n'] = d.ratio.rank(pct=True).clip(lower=0.05).astype('float32')
        preds.append(d[['cell_id', 'horizon', 'forecast_month', 'class', 'predicted', 'lo', 'hi', 'ratio', 'n', 'recent_data']])
        print('h', h, len(d), d['class'].value_counts().to_dict(), flush=True)
    p = pd.concat(preds, ignore_index=True).assign(model_version=version, generated_at=generated)
    p['ratio'] = p.ratio.astype('float32')
    p.sort_values(['cell_id', 'horizon']).to_parquet(os.path.join(out, 'predictions.parquet'), index=False, row_group_size=200_000)
    fits[1][4].to_parquet(os.path.join(out, 'features.parquet'), index=False)
    metrics = {'model_version': version, 'resolution_used': res, 'train_years': [F.Y0, F.TRAIN_LAST],
               'test_years': [F.TRAIN_LAST + 1, full[-1]], 'issue_month': f'{F.Y0 + last_t // 12}-{last_t % 12 + 1:02d}',
               'issue_month_outside_partial': f'{full[-1]}-12', 'seed': SEED, 'generated_at': generated,
               'class_rule': 'critico = top-10 % de P(critico) no treino; alto = top-25 % de P(alto+critico); baixo se P(baixo) >= 0,5',
               'drivers': 'ONI + histórico (NASA POWER fora desta versão)',
               'oni_recent': round(float(oni.get(last_full_t, oni.get(last_full_t - 1, 0.0))), 2),
               'horizons': {str(h): {**f[3], 'resolution_used': res} for h, f in fits.items()}}
    json.dump(metrics, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)
    print(json.dumps({h: {k: v for k, v in m.items() if k not in ('features', 'importances')} for h, m in metrics['horizons'].items()}, indent=1))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'data')
