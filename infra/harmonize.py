"""Harmoniza MODIS/Aqua e VIIRS numa série única (`viirs_eq`) para qualquer região do mundo e valida fora da amostra.

  python harmonize.py data/agg data

Regras (ver README):
- unidade: células-dia de ~1 km (cd01);
- elo AQUA<-SNPP: fator AQUA/SNPP calibrado em 2013-2019, validado em 2020-2021;
- elo N20<-SNPP: idem em 2019-2025; N21 ~ N20 (mesmo plano orbital);
- Aqua depois de 2021 nunca entra na calibração (deriva orbital);
- fator por célula 2° × mês; se faltar dado: bloco 10° × mês -> faixa de latitude 10° × mês -> global × mês
  (nunca um fator só global direto: hemisférios têm estações opostas);
- fonte por ano: AQUA 2003-2011, SNPP 2012-2025, N20 2026+.
Saídas: grid/{ano}.parquet, factors.csv, metrics.json.
"""
import glob, json, os, re, sys
import numpy as np
import pandas as pd

CAL, HOLD, N20_CAL = range(2013, 2020), range(2020, 2022), range(2019, 2026)
MIN_OBS = 100                       # células-dia VIIRS mínimas na calibração para confiar no fator daquele nível
SOURCE = {**{y: 'AQUA' for y in range(2003, 2012)}, **{y: 'SNPP' for y in range(2012, 2026)}, **{y: 'N20' for y in range(2026, 2031)}}
FILE = {'AQUA': 'modis', 'SNPP': 'viirs-snpp', 'N20': 'viirs-jpss1'}
N21_FACTOR = 1.0                    # ponytail: sem arquivo anual do N21; calibrar N21<-N20 com NRT quando houver 1 ano
LEVELS = [('c2', ['lat2', 'lon2']), ('c10', ['lat10', 'lon10']), ('band', ['lat10']), ('global', [])]


def _keys(df):
    """Chaves dos níveis a partir de lat05/lon05 (ou lat2/lon2)."""
    if 'lat2' not in df:
        df = df.assign(lat2=(np.floor(df.lat05 / 2) * 2).astype(int), lon2=(np.floor(df.lon05 / 2) * 2).astype(int))
    return df.assign(lat10=(np.floor(df.lat2 / 10) * 10).astype(int), lon10=(np.floor(df.lon2 / 10) * 10).astype(int))


def parts(agg_dir, sensor, year):
    return sorted(glob.glob(os.path.join(agg_dir, f'{FILE[sensor]}_{year}.csv.gz')) +
                  glob.glob(os.path.join(agg_dir, f'{FILE[sensor]}_{year}_*.csv.gz')))


def read_part(agg_dir, sensor, year):
    ps = parts(agg_dir, sensor, year)
    if not ps:
        return None
    d = pd.concat(pd.read_csv(p) for p in ps)
    return d[d.src == sensor]


def to_c2(d):
    """cd01 por sensor × ano × mês × célula 2° (dia + noite): o que a calibração precisa."""
    return _keys(d).groupby(['src', 'year', 'month', 'lat2', 'lon2'], as_index=False).cd01.sum()


def fit_factor(t, src_a, src_b, years, min_obs=MIN_OBS):
    """Fator A/B por nível hierárquico × mês. Um nível só vale se B >= min_obs e A > 0 (o global aceita B > 0)."""
    t = t[t.src.isin([src_a, src_b]) & t.year.isin(years)]
    p = t.pivot_table(index=['lat2', 'lon2', 'month'], columns='src', values='cd01', aggfunc='sum', fill_value=0)
    p = _keys(p.reindex(columns=[src_a, src_b], fill_value=0).set_axis(['A', 'B'], axis=1).reset_index())
    fit = {}
    for name, keys in LEVELS:
        s = p.groupby(keys + ['month'])[['A', 'B']].sum()
        need = s.B > 0 if name == 'global' else s.B >= min_obs
        fit[name] = (s.A / s.B).where(need & (s.A > 0)).dropna()
    return fit


def lookup(fit, df):
    """Fator e nível para cada linha (lat05/lon05 ou lat2/lon2, month), descendo a hierarquia até achar."""
    k = _keys(df)
    factor = np.full(len(k), np.nan)
    level = np.full(len(k), None, dtype=object)
    for name, keys in LEVELS:
        idx = pd.MultiIndex.from_frame(k[keys + ['month']]) if keys else pd.Index(k.month)
        v = fit[name].reindex(idx).to_numpy()
        hit = np.isnan(factor) & ~np.isnan(v)
        factor[hit], level[hit] = v[hit], name
    return factor, level


def holdout_metrics(t, fit):
    """Prevê AQUA a partir de SNPP em 2020-2021 (anos fora da calibração)."""
    h = t[t.src.isin(['AQUA', 'SNPP']) & t.year.isin(HOLD)]
    h = h.pivot_table(index=['year', 'month', 'lat2', 'lon2'], columns='src', values='cd01', aggfunc='sum', fill_value=0)
    h = h.reindex(columns=['AQUA', 'SNPP'], fill_value=0).set_axis(['A', 'B'], axis=1).reset_index()
    f, lvl = lookup(fit, h)
    h['pred'], h['level'] = h.B * f, lvl
    tot = h.groupby(['year', 'month'])[['A', 'pred']].sum()
    c = h[h.A >= 50]
    r = c.pred / c.A
    return {
        'holdout_years': [HOLD.start, HOLD.stop - 1], 'calibration_years': [CAL.start, CAL.stop - 1],
        'mape_total_monthly_pct': round(float((abs(tot.pred - tot.A) / tot.A).mean() * 100), 1),
        'r2_cell2_month': round(float(1 - ((c.pred - c.A) ** 2).sum() / ((c.A - c.A.mean()) ** 2).sum()), 3),
        'mdape_cell2_month_pct': round(float((abs(c.pred - c.A) / c.A).median() * 100), 1),
        'n_cell2_months': int(len(c)),
        'level_share': {k: round(float(v), 3) for k, v in c.level.value_counts(normalize=True).items()},
        'q10_q90_pred_over_actual': [round(float(r.quantile(.1)), 3), round(float(r.quantile(.9)), 3)],
    }


def grid_part(d, source, fit_aqua, fit_n20, q10, q90):
    """Uma fonte × ano -> série na moeda viirs_eq (células-dia como o VIIRS S-NPP veria), por célula 0,05° × mês."""
    g = d.groupby(['lat05', 'lon05', 'year', 'month'], as_index=False)[['raw', 'cd01']].sum()
    if source == 'SNPP':
        g['factor'], g['level'] = 1.0, 'observed'
    else:
        g['factor'], g['level'] = lookup(fit_aqua if source == 'AQUA' else fit_n20, g)
    g['source'] = source
    g['viirs_eq'] = g.cd01 / g.factor
    conv = source == 'AQUA'          # incerteza só onde a conversão é grande; anos VIIRS são observados
    g['lo'] = g.viirs_eq / q90 if conv else g.viirs_eq
    g['hi'] = g.viirs_eq / q10 if conv else g.viirs_eq
    return g[['lat05', 'lon05', 'year', 'month', 'source', 'raw', 'cd01', 'factor', 'level', 'viirs_eq', 'lo', 'hi']]


def factors_table(fit, link):
    rows = []
    for name, keys in LEVELS:
        s = fit[name].rename('factor').reset_index()
        s = s.rename(columns={'lat2': 'lat', 'lon2': 'lon', 'lat10': 'lat', 'lon10': 'lon'})
        rows.append(s.assign(link=link, level=name))
    return pd.concat(rows)[['link', 'level', 'lat', 'lon', 'month', 'factor']]


def main(agg_dir, out_dir):
    years = sorted({int(m) for p in glob.glob(os.path.join(agg_dir, '*.csv.gz')) for m in re.findall(r'_(\d{4})', p)[:1]})
    calib = [to_c2(d) for s in ('AQUA', 'SNPP', 'N20') for y in years
             if y in set(CAL) | set(HOLD) | set(N20_CAL) and (d := read_part(agg_dir, s, y)) is not None]
    t = pd.concat(calib)
    fit_aqua = fit_factor(t, 'AQUA', 'SNPP', CAL)
    fit_n20 = fit_factor(t, 'N20', 'SNPP', N20_CAL)
    m = holdout_metrics(t, fit_aqua)
    q10, q90 = m['q10_q90_pred_over_actual']
    os.makedirs(os.path.join(out_dir, 'grid'), exist_ok=True)
    rows = 0
    for y in years:
        src = SOURCE.get(y)
        d = read_part(agg_dir, src, y) if src else None
        if d is None or d.empty:
            continue
        g = grid_part(d, src, fit_aqua, fit_n20, q10, q90)
        g.to_parquet(os.path.join(out_dir, 'grid', f'{y}.parquet'), index=False)
        rows += len(g)
        print(y, src, len(g), 'linhas', flush=True)
    m.update(aqua_snpp_global_median=round(float(fit_aqua['global'].median()), 3),
             n20_snpp_global_median=round(float(fit_n20['global'].median()), 3) if len(fit_n20['global']) else None,
             grid_rows=rows, years=[years[0], years[-1]])
    pd.concat([factors_table(fit_aqua, 'AQUA_SNPP'), factors_table(fit_n20, 'N20_SNPP')]).to_csv(
        os.path.join(out_dir, 'factors.csv'), index=False)
    json.dump(m, open(os.path.join(out_dir, 'metrics.json'), 'w'), indent=1)
    print(json.dumps(m, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:3])
